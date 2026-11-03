---
name: model-interoperability
description: >
  Use when heterogeneous models, embeddings, adapters, or tools must work
  together across a boundary -- translating embeddings between vector spaces,
  composing LoRA/adapter experts, standardizing tool access (MCP), or making an
  attention/serving kernel plug into an existing stack. The recurring theme is a
  clean interface that preserves semantics while decoupling implementations.
status: active
last_validated: 2026-07-27
---

# Model Interoperability

Distilled from arXiv 2503.23278 (Model Context Protocol), 2505.1254 (universal
geometry of embeddings), 2505.18235 (representation manifolds), 2404.02948
(PiSSA), 2402.07148 (X-LoRA), 2501.01005 (FlashInfer), 2210.02747 (Flow
Matching), 2404.02882 (LASP).

## When to Use

- You need two independently-trained components to interoperate: embeddings from
  different models, adapters over a shared base, or a model behind a standardized
  tool interface.
- Preserving *semantic geometry* across the boundary matters -- a translated
  embedding or composed adapter must still mean the same thing.
- You want a customizable kernel/engine that adapts to varied settings rather
  than a hardwired one.

**Do NOT use when** a single self-contained model suffices -- interoperability
layers add surface area and security exposure. Note the barriers: MCP integration
raises cross-platform security concerns (2503.23278); embedding translation
cannot guarantee vector-DB security and rests on the universal-latent conjecture
(2505.1254).

## Core Concepts

- **Standardized tool interface (MCP, 2503.23278).** A single protocol lets any
  model reach external tools/resources, breaking data silos. Lifecycle = create,
  operate, update the server. Treat security (auth, injection) as a first-class
  design constraint, not an afterthought.

- **Embedding-space translation (2505.1254, 2505.18235).** Text embeddings from
  different architectures can be aligned *unsupervised*, without paired data,
  preserving cosine geometry -- enabling one model's vectors to be consumed by
  another. Grounded in the view that representations encode features as manifolds
  where distance maps to concept relatedness (linear representation hypothesis as
  starting assumption).

- **Composable adapters (PiSSA 2404.02948, X-LoRA 2402.07148).** Adapters over a
  shared frozen base are the interoperability unit: PiSSA updates principal
  singular components for fast convergence and stays quantization-compatible;
  X-LoRA dynamically gates a mixture of pre-trained LoRA experts layer-wise for
  domain-specific composition. Ship adapters, not whole models.

- **Customizable kernels/engines (FlashInfer 2501.01005, LASP 2404.02882).** An
  attention engine with a customizable template (block-sparse + JIT) plugs into
  SGLang/vLLM/MLC; linear-attention sequence parallelism is compatible with all
  batch-level data-parallel methods. Interoperability at the systems layer =
  compatibility with the existing serving/training stack.

- **Subsuming families (Flow Matching, 2210.02747).** A general formulation
  (Gaussian probability paths) that subsumes existing diffusion paths as special
  cases -- the interoperability move of finding the superset abstraction.

## Protocol

```
interoperate(component_A, component_B):
    iface <- define_interface()            # protocol / shared base / vector space
    if crossing_embedding_spaces:
        map  <- unsupervised_align(A_space, B_space)   # preserve cosine geometry
        emit <- map(A_vectors)
    elif composing_adapters:
        adapters <- {PiSSA|LoRA experts over shared frozen base}
        emit     <- dynamic_gate(adapters)             # layer-wise mixture
    elif standardizing_tools:
        server <- MCP(create -> operate -> update)     # secure by design
        emit   <- any_model.call(server)
    assert semantics_preserved(emit)       # geometry / behavior unchanged
    return emit
```

## Related

`bm25-corpus-sampling` (embedding evaluation), `active-inference` (shared latent
representations), `kg_ontology` (interface contracts between symbolic stores).
