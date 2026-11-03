"""Unit tests for cc_mmr.py (caption-band frame selector)."""
import os
import sys

import numpy as np
import pytest
from PIL import Image

import cc_mmr


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
CROP_W, CROP_H = 874, 180          # real caption band for an 874x720 source


def _unit(rows):
    """L2-normalise each row, as features() guarantees for its output."""
    a = np.asarray(rows, dtype=np.float32)
    return a / np.linalg.norm(a, axis=1, keepdims=True)


def _three_caption_groups():
    """9 frames = 3 distinct captions held on screen for 3 frames each.

    Within a group cosine == 1.0 (identical caption), across groups == 0.0.
    Relevance is arranged so the per-group winners are 1, 4 and 6.
    """
    vecs = _unit([
        [1, 0, 0, 0], [1, 0, 0, 0], [1, 0, 0, 0],
        [0, 1, 0, 0], [0, 1, 0, 0], [0, 1, 0, 0],
        [0, 0, 1, 0], [0, 0, 1, 0], [0, 0, 1, 0],
    ])
    rel = np.array([0.5, 0.9, 0.4, 0.3, 0.8, 0.2, 0.7, 0.1, 0.6], dtype=np.float32)
    return vecs, rel


def _write_png(path, painter):
    a = np.zeros((CROP_H, CROP_W), dtype=np.uint8)
    painter(a)
    Image.fromarray(a, mode="L").save(path)
    return str(path)


def _stripes(x0, x1):
    """Painter: hard black/white vertical stripes in [x0, x1) -> glyph-like edges."""
    def paint(a):
        a[:, x0:x1:4] = 255
        a[:, x0 + 1:x1:4] = 255
    return paint


# --------------------------------------------------------------------------
# mmr() -- redundancy gating
# --------------------------------------------------------------------------
def test_mmr_culls_repeated_captions_to_one_frame_each():
    """REGRESSION: a caption held across 3 frames must yield exactly 1 frame.

    The pre-fix code gated on the blended MMR score, which never falls below
    zero for populated frames, so it returned the entire timeline (9/9).
    """
    vecs, rel = _three_caption_groups()

    picked = cc_mmr.mmr(vecs, rel, lam=0.65, sim_max=0.9, max_pick=100)

    assert picked == [1, 4, 6]
    assert len(picked) == 3, "near-duplicate frames were not culled"


def test_mmr_returns_temporal_order():
    vecs, rel = _three_caption_groups()

    picked = cc_mmr.mmr(vecs, rel, lam=0.65, sim_max=0.9, max_pick=100)

    assert picked == sorted(picked)


def test_mmr_first_pick_is_most_salient_frame():
    vecs, rel = _three_caption_groups()

    picked = cc_mmr.mmr(vecs, rel, lam=0.65, sim_max=0.9, max_pick=1)

    assert picked == [1]            # rel[1] == 0.9 is the global max


def test_mmr_sim_max_of_one_disables_culling():
    """sim_max=1.0 -> similarity is never strictly greater, nothing is culled."""
    vecs, rel = _three_caption_groups()

    picked = cc_mmr.mmr(vecs, rel, lam=0.65, sim_max=1.0, max_pick=100)

    assert picked == list(range(9))


def test_mmr_lower_sim_max_is_never_less_aggressive():
    """Monotonicity: tightening the gate cannot increase the frame count."""
    vecs, rel = _three_caption_groups()

    loose = cc_mmr.mmr(vecs, rel, lam=0.65, sim_max=1.0, max_pick=100)
    tight = cc_mmr.mmr(vecs, rel, lam=0.65, sim_max=0.5, max_pick=100)

    assert len(tight) < len(loose)
    assert len(tight) == 3


def test_mmr_skips_blank_frames_with_zero_relevance():
    """Frames with no ink (salience 0) are not candidates at all."""
    vecs = _unit([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]])
    rel = np.array([0.0, 0.5, 0.0], dtype=np.float32)

    picked = cc_mmr.mmr(vecs, rel, lam=0.65, sim_max=0.9, max_pick=100)

    assert picked == [1]


def test_mmr_all_blank_returns_empty():
    vecs = _unit([[1, 0, 0, 0], [0, 1, 0, 0]])
    rel = np.zeros(2, dtype=np.float32)

    assert cc_mmr.mmr(vecs, rel, lam=0.65, sim_max=0.9, max_pick=100) == []


def test_mmr_respects_max_pick_cap():
    vecs, rel = _three_caption_groups()

    picked = cc_mmr.mmr(vecs, rel, lam=0.65, sim_max=0.9, max_pick=2)

    assert picked == [1, 4]


def test_mmr_culled_candidate_does_not_stall_the_loop():
    """Every frame identical -> exactly one survives and the loop terminates."""
    vecs = _unit([[1, 0], [1, 0], [1, 0], [1, 0]])
    rel = np.array([0.1, 0.4, 0.2, 0.3], dtype=np.float32)

    picked = cc_mmr.mmr(vecs, rel, lam=0.65, sim_max=0.9, max_pick=100)

    assert picked == [1]


# --------------------------------------------------------------------------
# features()
# --------------------------------------------------------------------------
def test_features_blank_frame_has_zero_salience_and_zero_vector(tmp_path):
    p = _write_png(tmp_path / "blank.png", lambda a: None)

    vec, salience = cc_mmr.features(p)

    assert salience == 0.0
    assert np.linalg.norm(vec) == 0.0        # exercises the n == 0 branch


def test_features_vector_has_grid_shape(tmp_path):
    p = _write_png(tmp_path / "text.png", _stripes(100, 400))

    vec, _ = cc_mmr.features(p)

    assert vec.shape == (8 * 48,)


def test_features_text_frame_is_salient_and_unit_norm(tmp_path):
    p = _write_png(tmp_path / "text.png", _stripes(100, 400))

    vec, salience = cc_mmr.features(p)

    assert salience > 0.0
    assert np.linalg.norm(vec) == pytest.approx(1.0, abs=1e-5)


def test_features_is_deterministic(tmp_path):
    a = _write_png(tmp_path / "a.png", _stripes(100, 400))
    b = _write_png(tmp_path / "b.png", _stripes(100, 400))

    va, sa = cc_mmr.features(a)
    vb, sb = cc_mmr.features(b)

    assert np.array_equal(va, vb)
    assert sa == sb


def test_features_different_ink_position_gives_dissimilar_vectors(tmp_path):
    """The property MMR relies on: different caption text -> different vector."""
    left = _write_png(tmp_path / "left.png", _stripes(0, 400))
    right = _write_png(tmp_path / "right.png", _stripes(474, 864))

    vl, _ = cc_mmr.features(left)
    vr, _ = cc_mmr.features(right)

    assert float(vl @ vr) == pytest.approx(0.0, abs=1e-6)


def test_features_same_ink_position_gives_similar_vectors(tmp_path):
    """Sanity counterpart: overlapping ink must score far above the cull gate."""
    a = _write_png(tmp_path / "a.png", _stripes(100, 400))
    b = _write_png(tmp_path / "b.png", _stripes(100, 404))

    va, _ = cc_mmr.features(a)
    vb, _ = cc_mmr.features(b)

    assert float(va @ vb) > 0.9


def test_features_denser_text_scores_higher_salience(tmp_path):
    sparse = _write_png(tmp_path / "sparse.png", _stripes(100, 200))
    dense = _write_png(tmp_path / "dense.png", _stripes(100, 800))

    _, s_sparse = cc_mmr.features(sparse)
    _, s_dense = cc_mmr.features(dense)

    assert s_dense > s_sparse


# --------------------------------------------------------------------------
# probe() / extract() -- geometry contract
# --------------------------------------------------------------------------
def test_probe_parses_ffprobe_csv(monkeypatch):
    monkeypatch.setattr(cc_mmr.subprocess, "check_output",
                        lambda *a, **k: "874x720\n")

    assert cc_mmr.probe("clip.mp4") == (874, 720)


@pytest.mark.parametrize("band, exp_h, exp_y", [
    (0.25, 180, 540),      # lower quarter of a 720p-tall frame
    (0.20, 144, 576),
    (1.00, 720, 0),        # whole frame
])
def test_extract_crops_the_bottom_band(monkeypatch, tmp_path, band, exp_h, exp_y):
    captured = {}
    monkeypatch.setattr(cc_mmr, "probe", lambda v: (874, 720))
    monkeypatch.setattr(cc_mmr.subprocess, "check_call",
                        lambda cmd: captured.setdefault("cmd", cmd))

    frames, geom = cc_mmr.extract("clip.mp4", str(tmp_path / "out"), 1.0, band)

    vf = captured["cmd"][captured["cmd"].index("-vf") + 1]
    assert vf == f"fps=1.0,crop=874:{exp_h}:0:{exp_y}"
    assert geom == (874, exp_h, exp_y)
    assert frames == []


def test_extract_clears_a_stale_output_dir(monkeypatch, tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "f_0001.png").write_bytes(b"stale")
    monkeypatch.setattr(cc_mmr, "probe", lambda v: (874, 720))
    monkeypatch.setattr(cc_mmr.subprocess, "check_call", lambda cmd: None)

    frames, _ = cc_mmr.extract("clip.mp4", str(out), 1.0, 0.25)

    assert frames == []
    assert not (out / "f_0001.png").exists()


# --------------------------------------------------------------------------
# main() -- CLI wiring
# --------------------------------------------------------------------------
def _stub_pipeline(monkeypatch, tmp_path, n_frames=6, group=2):
    """Mock extract/features so main() runs offline. Returns the mmr call log."""
    def fake_extract(video, outdir, fps, band):
        os.makedirs(outdir, exist_ok=True)
        names = []
        for i in range(n_frames):
            name = f"f_{i:04d}.png"
            Image.fromarray(np.zeros((4, 4), np.uint8), mode="L").save(
                os.path.join(outdir, name))
            names.append(name)
        return sorted(names), (874, 180, 540)

    def fake_features(path):
        idx = int(os.path.basename(path)[2:6])
        v = np.zeros(8, dtype=np.float32)
        v[idx // group] = 1.0            # `group` consecutive frames share a caption
        return v, 0.5

    calls = {}
    real_mmr = cc_mmr.mmr

    def spy_mmr(vecs, rel, lam, sim_max, max_pick):
        calls.update(lam=lam, sim_max=sim_max, max_pick=max_pick)
        return real_mmr(vecs, rel, lam, sim_max, max_pick)

    monkeypatch.setattr(cc_mmr, "extract", fake_extract)
    monkeypatch.setattr(cc_mmr, "features", fake_features)
    monkeypatch.setattr(cc_mmr, "mmr", spy_mmr)
    return calls


def test_main_defaults_to_sim_max_097(monkeypatch, tmp_path, capsys):
    """Guards the flag rename: a stale args.sim_cut would raise AttributeError."""
    out = tmp_path / "out"
    calls = _stub_pipeline(monkeypatch, tmp_path)
    monkeypatch.setattr(sys, "argv",
                        ["cc_mmr.py", str(tmp_path / "clip.mp4"), "--outroot", str(out)])

    cc_mmr.main()

    assert calls["sim_max"] == 0.97
    assert calls["lam"] == 0.65


def test_main_selects_one_frame_per_caption(monkeypatch, tmp_path, capsys):
    out = tmp_path / "out"
    _stub_pipeline(monkeypatch, tmp_path, n_frames=6, group=2)
    monkeypatch.setattr(sys, "argv",
                        ["cc_mmr.py", str(tmp_path / "clip.mp4"), "--outroot", str(out)])

    cc_mmr.main()

    picked = sorted(os.listdir(out / "salient"))
    assert len(picked) == 3, f"expected 3 deduped frames, got {picked}"
    assert "[mmr] lambda=0.65 selected 3/6" in capsys.readouterr().out


def test_main_writes_manifest_with_timestamps(monkeypatch, tmp_path, capsys):
    out = tmp_path / "out"
    _stub_pipeline(monkeypatch, tmp_path, n_frames=6, group=2)
    monkeypatch.setattr(sys, "argv",
                        ["cc_mmr.py", str(tmp_path / "clip.mp4"),
                         "--outroot", str(out), "--fps", "2"])

    cc_mmr.main()

    rows = (out / "manifest.tsv").read_text(encoding="utf-8").strip().splitlines()
    assert rows[0] == "file\ttime_s\tsalience"
    assert len(rows) == 4                       # header + 3 frames

    times = []
    for row in rows[1:]:
        name, t_s, _ = row.split("\t")
        frame_idx = int(name.split("_f")[1].split(".")[0])
        times.append(float(t_s))
        # --fps 2 -> each frame index is half a second apart
        assert float(t_s) == pytest.approx(frame_idx / 2.0)
        assert name.startswith(f"t{int(frame_idx / 2.0):04d}s_")
    assert times == sorted(times), "manifest must be in temporal order"


def test_main_cli_sim_max_overrides_default(monkeypatch, tmp_path, capsys):
    out = tmp_path / "out"
    calls = _stub_pipeline(monkeypatch, tmp_path, n_frames=6, group=2)
    monkeypatch.setattr(sys, "argv",
                        ["cc_mmr.py", str(tmp_path / "clip.mp4"),
                         "--outroot", str(out), "--sim-max", "1.0"])

    cc_mmr.main()

    assert calls["sim_max"] == 1.0
    assert len(os.listdir(out / "salient")) == 6      # culling disabled


# --------------------------------------------------------------------------
# regression: the 0.90 gate silently dropped real caption changes
# --------------------------------------------------------------------------
def _at_angles(degrees_from_first):
    """Unit vectors at given angles, so cosine similarity is exactly cos(dtheta)."""
    return _unit([[np.cos(np.deg2rad(d)), np.sin(np.deg2rad(d))]
                  for d in degrees_from_first])


def test_mmr_keeps_distinct_captions_that_share_a_screen_region():
    """Three DIFFERENT captions rendered in the same band score ~0.93 against
    each other, because the 8x48 stroke-density grid is too coarse to tell
    them apart.  At sim_max=0.97 all three survive; at 0.90 one is wrongly
    culled as a duplicate.  This is the bug that ate the quote after
    'and... and... I quote:' in the source clip.
    """
    theta = np.rad2deg(np.arccos(0.93))
    vecs = _at_angles([0.0, theta, 2 * theta])
    rel = np.array([1.0, 1.0, 1.0], dtype=np.float32)

    # sanity: the fixture really does sit in the contested 0.90-0.97 band
    S = vecs @ vecs.T
    assert S[0, 1] == pytest.approx(0.93, abs=1e-4)
    assert S[1, 2] == pytest.approx(0.93, abs=1e-4)

    assert cc_mmr.mmr(vecs, rel, 0.65, 0.97, max_pick=99) == [0, 1, 2]
    assert cc_mmr.mmr(vecs, rel, 0.65, 0.90, max_pick=99) == [0, 2]


def test_mmr_still_culls_a_held_caption():
    """A caption held on screen scores ~0.995 frame-to-frame and must go."""
    theta = np.rad2deg(np.arccos(0.995))
    vecs = _at_angles([0.0, theta])
    rel = np.array([1.0, 1.0], dtype=np.float32)
    assert cc_mmr.mmr(vecs, rel, 0.65, 0.97, max_pick=99) == [0]
