---
name: pyo3-python-extension
description: Scaffold and guide building a Rust-to-Python native extension using PyO3 and maturin â€” generates a working Cargo.toml + src/lib.rs with #[pyclass]/#[pymethods] boilerplate that exposes a Rust struct (or function) to Python, and explains the build/packaging workflow (maturin develop/build, the extension-module feature, release-profile tuning for hot loops). Use this whenever the user wants to wrap Rust code for Python, mentions PyO3, maturin, cdylib, or "extension module", or asks to port a slow Python function/loop to Rust for speed. Also trigger when debugging an existing PyO3 crate's build or packaging â€” maturin develop failures, pyclass/pymethods errors, cdylib linking issues, or "why isn't my Rust speedup showing up in Python".
---

# PyO3 Python Extension

## When this applies

Someone wants Python code to call into compiled Rust â€” usually because a loop, search, or numeric core is too slow in pure Python. PyO3 + maturin is the standard pairing for this: PyO3 generates the CPython-compatible extension module from annotated Rust, maturin builds and installs it as a normal Python package.

## The one thing that determines whether this actually helps

The FFI crossing itself is cheap, but it happens once per call into Rust â€” not once per operation inside Rust. The speedup comes entirely from how much work happens on the Rust side of a *single* crossing.

- **Good:** Python calls `.search(fen, depth)` once; the entire tree walk (all the way down to the leaves) runs as compiled Rust. One crossing, unbounded native work underneath.
- **Bad:** Python calls into Rust for every node of a search tree. Now you pay the FFI overhead per node, and most of the "speedup" is eaten by crossings.

Before scaffolding anything, figure out where the natural boundary is: the coarsest-grained call that still expresses everything Python needs to know. Design the `#[pyclass]`/`#[pymethods]` surface around *that* boundary, not around every internal function.

## Steps

### 1. Decide the boundary

Ask: what does Python actually need back â€” a single number, a struct, a stream of results? Everything on the Rust side of that answer should live entirely in Rust. Don't expose internal helper functions as separate PyO3 methods unless Python genuinely needs to call them independently; every extra `#[pymethods]` entry is a potential extra crossing point and a wider surface to keep type-safe.

### 2. Set up the crate

`Cargo.toml` needs three things beyond a normal crate: the `cdylib` crate type (so it builds as a shared library shaped like a CPython extension), the `pyo3` dependency with the `extension-module` feature, and â€” if this is a hot-loop use case â€” a tuned release profile.

```toml
[lib]
crate-type = ["cdylib"]

[dependencies]
pyo3 = { version = "0.28", features = ["extension-module"] }

[profile.release]
lto = true
codegen-units = 1
```

(`0.28` is current as of writing â€” check [crates.io/crates/pyo3](https://crates.io/crates/pyo3) for the latest, since PyO3's pre-1.0 versioning means a minor bump, e.g. 0.22 â†’ 0.23, can be a breaking change under Cargo's semver rules. The `Bound<'_, T>` API used throughout this skill has been stable since 0.21, so it works across the 0.21â€“0.28 range regardless of exact pin.)

`lto = true` + `codegen-units = 1` trade compile time for runtime speed by letting the optimizer see across the whole crate â€” worth it for a hot path, not worth it for a crate you're rebuilding every few seconds during development (skip it, or keep it in `[profile.release]` only, while iterating with plain `cargo build`).

### 3. Expose the struct

```rust
use pyo3::prelude::*;

#[pyclass]
struct Searcher {
    weights: Vec<f32>,
    bias: f32,
}

#[pymethods]
impl Searcher {
    #[new]
    fn new(weights: Vec<f32>, bias: f32) -> Self {
        Searcher { weights, bias }
    }

    fn search(&self, fen: &str, depth: u32) -> PyResult<String> {
        // full alpha-beta walk happens here, natively, before returning
        todo!()
    }
}

#[pymodule]
fn my_crate_name(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Searcher>()?;
    Ok(())
}
```

`#[new]` is the constructor PyO3 wires to `__init__`. Every `#[pymethods]` fn becomes a normal-looking Python method â€” `Searcher(w, b).search(fen, depth)` from the Python side, no different from calling a pure-Python object.

Note the `#[pymodule]` signature takes `&Bound<'_, PyModule>` â€” PyO3 0.21 replaced the old `&PyModule`/`Python` "GIL Refs" API with the `Bound<'_, T>` smart pointer. If you're reading older PyO3 examples (blog posts, older crates) that show `fn my_crate_name(_py: Python, m: &PyModule)`, that's the pre-0.21 API and will not compile against a modern `pyo3` dependency â€” this is a real, easy-to-hit trap, not a style preference.

### 4. Build and install

```bash
maturin develop --release   # builds + installs into the active venv's site-packages
```

Use `maturin develop` (no `--release`) while iterating on correctness â€” faster compiles, slower runtime, fine for a tight edit/test loop. Switch to `--release` once you're benchmarking or shipping; that's what actually engages the LTO/codegen-units profile from step 2. `maturin build` produces a wheel instead of installing in place, for when the package needs to go somewhere else (CI artifact, PyPI, another machine).

### 5. Type safety stops at the FFI boundary â€” validate what's inside it

PyO3 enforces the *shape* of the boundary: call `Searcher(weights, bias)` with the wrong argument types or arity and it raises a `TypeError` before Rust code runs. It does **not** validate semantic correctness â€” a malformed FEN string, a wrong-length weight vector, an out-of-range depth all pass the type check and fail (or silently misbehave) inside Rust. If those inputs come from anywhere other than trusted internal code, validate them explicitly in `new`/the method body, not just via the type signature.

## Scaffold script

`scripts/scaffold_pyo3_crate.py` generates a working `Cargo.toml` + `src/lib.rs` skeleton from a struct name, field list, and method signatures, so you're editing a compiling starting point instead of writing the boilerplate by hand. Run it, then fill in the actual method bodies.

```bash
python scripts/scaffold_pyo3_crate.py \
  --crate-name my_crate \
  --struct-name Searcher \
  --field "weights:Vec<f32>" --field "bias:f32" \
  --method "search(fen:&str,depth:u32)->PyResult<String>" \
  --out-dir ./my_crate
```

It writes `<out-dir>/Cargo.toml` and `<out-dir>/src/lib.rs` with the crate-type, pyo3 dependency, `#[pyclass]`, `#[new]`, one stub per `--method`, and the `#[pymodule]` registration already wired up. It does not write method bodies (those are `todo!()` stubs) or a release profile â€” add `[profile.release]` tuning yourself only if this is actually a hot-loop crate (step 2 above explains the tradeoff).

## Worked example: rsearch4

A chess search engine (`rsearch4`) exposes a `Searcher` built from a flat weight vector + bias:

- Crate: `cdylib`, `pyo3 = "0.22"` with `extension-module`, release profile with `lto = true` and `codegen-units = 1`.
- `Searcher` is `#[pyclass]`/`#[pymethods]` with `.search(fen, depth)` and `.score(fen)` â€” Python calls these like normal object methods (`Searcher(w, b).search(fen, depth)`).
- Move generation inside the crate comes from `cozy-chess`; the entire alpha-beta walk for a `.search()` call happens natively before anything crosses back to Python.
- Build/dev loop: `maturin develop --release` from the crate directory, which installs into `site-packages/rsearch4/` like a normal package.
- Result: ~13Ã— wall-clock over an equivalent Python-side tree, because the FFI crossing happens once per `.search()` call rather than once per node â€” exactly the "good" boundary from the section above.

If asked to add a new capability to a crate shaped like this (e.g. a new backup/scoring rule), keep it as a new or extended `#[pymethods]` entry on the existing pyclass rather than a new standalone PyO3 function â€” one coherent object, one constructor, growing method surface.