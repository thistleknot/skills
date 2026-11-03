"""
Targeted gap refinement for cc_mmr.py output.

Re-samples ONLY the given time windows at a finer fps, then uses the same
stroke-density features to decide which of those frames are actually novel
against the captions we already have.  Extraction is cheap; LLM transcription
is not -- so the point of this script is to hand the transcriber only frames
that carry text we have not already seen.

Usage:
    python gapfill.py <video> --windows 126-135,152-172 --ref <dir>[,<dir>...]
"""
import argparse
import os
import shutil
import subprocess

import numpy as np

import cc_mmr


def extract_window(video, outdir, start, end, fps, w, ch, cy, tag):
    vf = f"fps={fps},crop={w}:{ch}:0:{cy}"
    cmd = ["ffmpeg", "-v", "error", "-ss", str(start), "-i", video,
           "-t", str(end - start), "-vf", vf, "-vsync", "0",
           os.path.join(outdir, f"w{tag}_%04d.png")]
    subprocess.check_call(cmd)
    out = []
    for name in sorted(os.listdir(outdir)):
        if not name.startswith(f"w{tag}_"):
            continue
        idx = int(name.split("_")[1].split(".")[0])
        out.append((start + (idx - 1) / fps, os.path.join(outdir, name)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--windows", required=True,
                    help="comma-separated START-END pairs in seconds")
    ap.add_argument("--ref", required=True,
                    help="comma-separated dirs of already-transcribed frames")
    ap.add_argument("--fps", type=float, default=2.0)
    ap.add_argument("--band", type=float, default=0.25)
    ap.add_argument("--sim-max", type=float, default=0.97)
    ap.add_argument("--floor", type=float, required=True,
                    help="text-salience floor from the parent cc_mmr run")
    ap.add_argument("--outroot", required=True)
    args = ap.parse_args()

    w, h = cc_mmr.probe(args.video)
    ch = int(round(h * args.band))
    cy = h - ch

    raw = os.path.join(args.outroot, "raw")
    keep_dir = os.path.join(args.outroot, "novel")
    for d in (raw, keep_dir):
        if os.path.isdir(d):
            shutil.rmtree(d)
        os.makedirs(d)

    # --- reference: every frame we already have a transcription for
    ref = []
    for d in args.ref.split(","):
        for name in sorted(os.listdir(d)):
            if name.endswith(".png"):
                vec, _ = cc_mmr.features(os.path.join(d, name))
                if np.linalg.norm(vec) > 0:
                    ref.append(vec)
    ref = np.asarray(ref, dtype=np.float32)
    print(f"[ref] {len(ref)} already-transcribed frames")

    # --- extract each window at the finer rate
    cands = []
    for win in args.windows.split(","):
        a, b = (float(x) for x in win.split("-"))
        cands += extract_window(args.video, raw, a, b, args.fps, w, ch, cy,
                                tag=f"{int(a):04d}")
    print(f"[extract] {len(cands)} frames @{args.fps}fps across "
          f"{len(args.windows.split(','))} windows")

    # --- novelty gate: keep only frames unlike anything already transcribed
    known = list(ref)
    kept, blank, dup = [], 0, 0
    for t, path in sorted(cands):
        vec, sal = cc_mmr.features(path)
        if sal < args.floor or np.linalg.norm(vec) == 0:
            blank += 1
            continue
        if known and max(float(vec @ k) for k in known) > args.sim_max:
            dup += 1
            continue
        known.append(vec)
        name = f"t{int(t):04d}s_{t:07.2f}.png".replace(".", "p", 1)
        dst = os.path.join(keep_dir, f"g{t:07.2f}.png".replace(".", "p", 1))
        shutil.copyfile(path, dst)
        kept.append((t, dst, sal))

    print(f"[gate] blank={blank} duplicate={dup} NOVEL={len(kept)}")
    for t, dst, sal in kept:
        print(f"   t={t:7.2f}s  sal={sal:.4f}  {os.path.basename(dst)}")


if __name__ == "__main__":
    main()
