"""Unit tests for gapfill.py (targeted gap re-sampling + novelty gate)."""
import os
import sys

import numpy as np
import pytest

import cc_mmr
import gapfill


def _touch(path, n=1):
    """Create n dummy png files named f_0001.png ... in path."""
    os.makedirs(path, exist_ok=True)
    made = []
    for i in range(1, n + 1):
        p = os.path.join(path, f"f_{i:04d}.png")
        with open(p, "wb") as fh:
            fh.write(b"\x89PNG")
        made.append(p)
    return made


# --------------------------------------------------------------------------
# extract_window() -- timestamp arithmetic
# --------------------------------------------------------------------------
def test_extract_window_maps_index_to_absolute_time(monkeypatch, tmp_path):
    """Frame k of a window starting at S is at S + (k-1)/fps, NOT k/fps.

    Off-by-one here silently mislabels every recovered caption's timestamp.
    """
    out = tmp_path / "raw"
    out.mkdir()

    def fake_call(cmd):
        for i in range(1, 5):
            (out / f"w0126_{i:04d}.png").write_bytes(b"\x89PNG")

    monkeypatch.setattr(gapfill.subprocess, "check_call", fake_call)

    got = gapfill.extract_window("v.mp4", str(out), 126.0, 128.0, 2.0,
                                 874, 180, 540, tag="0126")

    assert [t for t, _ in got] == [126.0, 126.5, 127.0, 127.5]


def test_extract_window_ignores_frames_from_other_windows(monkeypatch, tmp_path):
    """Windows share one raw dir; a window must only claim its own tag."""
    out = tmp_path / "raw"
    out.mkdir()
    (out / "w0035_0001.png").write_bytes(b"\x89PNG")      # a previous window

    def fake_call(cmd):
        (out / "w0126_0001.png").write_bytes(b"\x89PNG")

    monkeypatch.setattr(gapfill.subprocess, "check_call", fake_call)

    got = gapfill.extract_window("v.mp4", str(out), 126.0, 127.0, 2.0,
                                 874, 180, 540, tag="0126")

    assert len(got) == 1
    assert got[0][0] == 126.0
    assert os.path.basename(got[0][1]) == "w0126_0001.png"


def test_extract_window_passes_crop_and_seek_to_ffmpeg(monkeypatch, tmp_path):
    captured = {}
    out = tmp_path / "raw"
    out.mkdir()

    def fake_call(cmd):
        captured["cmd"] = cmd

    monkeypatch.setattr(gapfill.subprocess, "check_call", fake_call)
    gapfill.extract_window("v.mp4", str(out), 152.0, 172.0, 2.0,
                           874, 180, 540, tag="0152")

    cmd = captured["cmd"]
    assert "fps=2.0,crop=874:180:0:540" in cmd
    assert cmd[cmd.index("-ss") + 1] == "152.0"
    assert cmd[cmd.index("-t") + 1] == "20.0"        # duration, not end time
    assert cmd.index("-ss") < cmd.index("-i"), "seek must precede -i"


# --------------------------------------------------------------------------
# main() -- the novelty gate
# --------------------------------------------------------------------------
def _run_main(monkeypatch, tmp_path, frames, ref_vec, floor=0.5, sim_max=0.97):
    """frames: list of (t, basename, vec, salience). Returns captured stdout."""
    ref_dir = tmp_path / "ref"
    _touch(str(ref_dir), 1)
    raw_src = tmp_path / "src"
    raw_src.mkdir(exist_ok=True)      # helper runs twice in one test

    table = {}
    cands = []
    for t, name, vec, sal in frames:
        p = raw_src / name
        p.write_bytes(b"\x89PNG")
        table[name] = (np.asarray(vec, dtype=np.float32), sal)
        cands.append((t, str(p)))
    table["f_0001.png"] = (np.asarray(ref_vec, dtype=np.float32), 1.0)

    monkeypatch.setattr(cc_mmr, "probe", lambda v: (874, 720))
    monkeypatch.setattr(cc_mmr, "features",
                        lambda p: table[os.path.basename(p)])
    monkeypatch.setattr(gapfill, "extract_window",
                        lambda *a, **k: cands)

    out = tmp_path / "out"
    monkeypatch.setattr(sys, "argv", [
        "gapfill.py", "v.mp4", "--windows", "10-20",
        "--ref", str(ref_dir), "--floor", str(floor),
        "--sim-max", str(sim_max), "--outroot", str(out)])
    gapfill.main()
    return out


def test_gate_keeps_novel_culls_duplicate_and_blank(monkeypatch, tmp_path, capsys):
    out = _run_main(monkeypatch, tmp_path, ref_vec=[1.0, 0.0], frames=[
        (10.0, "dup.png",   [1.0, 0.0], 1.0),    # identical to reference
        (10.5, "blank.png", [0.0, 1.0], 0.0),    # below salience floor
        (11.0, "novel.png", [0.0, 1.0], 1.0),    # unseen caption
    ])

    txt = capsys.readouterr().out
    assert "blank=1 duplicate=1 NOVEL=1" in txt
    assert os.listdir(out / "novel") == ["g0011p00.png"]


def test_gate_deduplicates_among_novel_frames(monkeypatch, tmp_path, capsys):
    """A caption held across the gap must be recovered once, not twice."""
    out = _run_main(monkeypatch, tmp_path, ref_vec=[1.0, 0.0], frames=[
        (10.0, "a.png", [0.0, 1.0], 1.0),
        (10.5, "b.png", [0.0, 1.0], 1.0),        # same new caption, next frame
    ])

    assert "NOVEL=1" in capsys.readouterr().out
    assert len(os.listdir(out / "novel")) == 1


def test_gate_boundary_is_strictly_greater_than_sim_max(monkeypatch, tmp_path, capsys):
    """sim exactly == sim_max is NOT a duplicate (matches cc_mmr.mmr)."""
    _run_main(monkeypatch, tmp_path, ref_vec=[1.0, 0.0], sim_max=1.0, frames=[
        (10.0, "exact.png", [1.0, 0.0], 1.0),
    ])

    assert "NOVEL=1" in capsys.readouterr().out


def test_looser_sim_max_recovers_more_frames(monkeypatch, tmp_path, capsys):
    """The 0.90-vs-0.97 lesson: a stricter gate hides real caption changes."""
    theta = np.arccos(0.93)
    near = [float(np.cos(theta)), float(np.sin(theta))]

    _run_main(monkeypatch, tmp_path, ref_vec=[1.0, 0.0], sim_max=0.90,
              frames=[(10.0, "n.png", near, 1.0)])
    assert "NOVEL=0" in capsys.readouterr().out

    _run_main(monkeypatch, tmp_path, ref_vec=[1.0, 0.0], sim_max=0.97,
              frames=[(10.0, "n.png", near, 1.0)])
    assert "NOVEL=1" in capsys.readouterr().out


def test_outroot_is_cleared_between_runs(monkeypatch, tmp_path, capsys):
    """Stale frames from an earlier run must not pollute the novel set."""
    out = tmp_path / "out"
    (out / "novel").mkdir(parents=True)
    (out / "novel" / "stale.png").write_bytes(b"\x89PNG")

    _run_main(monkeypatch, tmp_path, ref_vec=[1.0, 0.0], frames=[
        (10.0, "novel.png", [0.0, 1.0], 1.0),
    ])

    assert "stale.png" not in os.listdir(out / "novel")


def test_zero_norm_reference_frames_are_skipped(monkeypatch, tmp_path, capsys):
    """A blank reference frame has a zero vector and would poison the dot product."""
    _run_main(monkeypatch, tmp_path, ref_vec=[0.0, 0.0], frames=[
        (10.0, "novel.png", [0.0, 1.0], 1.0),
    ])

    txt = capsys.readouterr().out
    assert "[ref] 0 already-transcribed frames" in txt
    assert "NOVEL=1" in txt
