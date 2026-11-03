"""
Extract 1fps frames from a video, crop to the lower 25% (caption band),
score each crop for text salience, and select a diverse/salient subset via MMR.

Usage:
    python cc_mmr.py <video> [--fps 1] [--band 0.25] [--lambda 0.65]
"""
import argparse
import os
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image


def probe(video):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0:s=x", video,
    ], text=True).strip().splitlines()[0]
    w, h = out.split("x")[:2]
    return int(w), int(h)


def extract(video, outdir, fps, band):
    w, h = probe(video)
    ch = int(round(h * band))
    cy = h - ch
    if os.path.isdir(outdir):
        shutil.rmtree(outdir)
    os.makedirs(outdir)
    vf = f"fps={fps},crop={w}:{ch}:0:{cy}"
    cmd = ["ffmpeg", "-v", "error", "-i", video, "-vf", vf,
           "-vsync", "0",
           os.path.join(outdir, "f_%04d.png")]
    subprocess.check_call(cmd)
    frames = sorted(os.listdir(outdir))
    print(f"[extract] {w}x{h} -> crop {w}x{ch} @y={cy}; {len(frames)} frames @{fps}fps")
    return frames, (w, ch, cy)


def features(path):
    """Return (feature_vector, text_salience) for one caption-band crop."""
    im = Image.open(path).convert("L")
    a = np.asarray(im, dtype=np.float32) / 255.0

    # --- text salience: captions are high-contrast glyph strokes on flat bg.
    gx = np.abs(np.diff(a, axis=1))
    gy = np.abs(np.diff(a, axis=0))
    edge = np.zeros_like(a)
    edge[:, :-1] += gx
    edge[:-1, :] += gy
    strong = edge > 0.25                      # stroke edges, not gradients
    salience = float(strong.mean())

    # --- feature vector: coarse spatial grid of stroke density.
    #     Captures WHERE ink sits -> different caption text = different vector.
    gh, gw = 8, 48
    H, W = strong.shape
    ph, pw = H // gh, W // gw
    grid = strong[: gh * ph, : gw * pw].reshape(gh, ph, gw, pw).mean(axis=(1, 3))
    v = grid.ravel().astype(np.float32)
    n = np.linalg.norm(v)
    return (v / n if n > 0 else v), salience


def mmr(vecs, rel, lam, sim_max, max_pick):
    """Maximal Marginal Relevance selection. Returns indices in temporal order.

    sim_max gates REDUNDANCY directly: a candidate whose cosine similarity to
    any already-picked frame exceeds sim_max is a near-duplicate (same caption
    still on screen) and is culled outright.  Gating on the blended MMR score
    instead does not work -- with rel normalised to <=1 the score floors at
    lam*rel - (1-lam), which stays positive for every populated frame, so no
    candidate is ever rejected and the selector returns the whole timeline.
    """
    S = vecs @ vecs.T                       # cosine (vecs are L2-normalised)
    cand = [i for i in range(len(vecs)) if rel[i] > 0]
    picked = []
    while cand and len(picked) < max_pick:
        if not picked:
            best = max(cand, key=lambda i: rel[i])
        else:
            scored = [(lam * rel[i] - (1 - lam) * max(S[i, j] for j in picked), i)
                      for i in cand]
            _, best = max(scored)
            if max(S[best, j] for j in picked) > sim_max:
                cand.remove(best)        # near-duplicate -> cull, keep going
                continue
        picked.append(best)
        cand.remove(best)
    return sorted(picked)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--fps", type=float, default=1.0)
    ap.add_argument("--band", type=float, default=0.25)
    ap.add_argument("--lam", type=float, default=0.65)
    ap.add_argument("--sim-max", type=float, default=0.97,
                    help="cull a frame whose cosine similarity to an already-"
                         "selected frame exceeds this (same caption still up). "
                         "0.90 measurably over-culls: the 8x48 stroke-density "
                         "grid is coarse enough that two DIFFERENT captions "
                         "occupying the same screen region score >0.90, so "
                         "real caption changes get dropped as duplicates.")
    ap.add_argument("--outroot", default=None)
    args = ap.parse_args()

    stem = os.path.splitext(os.path.basename(args.video))[0]
    root = args.outroot or os.path.join(os.path.dirname(args.video), "cc_frames", stem)
    raw = os.path.join(root, "_all")
    sel = os.path.join(root, "salient")

    frames, geom = extract(args.video, raw, args.fps, args.band)
    if not frames:
        sys.exit("no frames extracted")

    vecs, rel = [], []
    for f in frames:
        v, s = features(os.path.join(raw, f))
        vecs.append(v)
        rel.append(s)
    vecs = np.vstack(vecs)
    rel = np.array(rel, dtype=np.float32)

    # Blank / no-caption frames: salience far below the populated frames.
    active = rel[rel > 0]
    floor = (active.max() * 0.15) if active.size else 0.0
    relN = np.where(rel >= floor, rel, 0.0)
    if relN.max() > 0:
        relN = relN / relN.max()

    print(f"[salience] floor={floor:.5f}  "
          f"frames_with_text={(relN > 0).sum()}/{len(frames)}")

    keep = mmr(vecs, relN, args.lam, args.sim_max, max_pick=len(frames))

    if os.path.isdir(sel):
        shutil.rmtree(sel)
    os.makedirs(sel)
    manifest = []
    for i in keep:
        t = i / args.fps
        name = f"t{int(t):04d}s_f{i:04d}.png"
        shutil.copyfile(os.path.join(raw, frames[i]), os.path.join(sel, name))
        manifest.append((name, t, float(relN[i])))

    with open(os.path.join(root, "manifest.tsv"), "w", encoding="utf-8") as fh:
        fh.write("file\ttime_s\tsalience\n")
        for name, t, s in manifest:
            fh.write(f"{name}\t{t:.1f}\t{s:.4f}\n")

    print(f"[mmr] lambda={args.lam} selected {len(keep)}/{len(frames)}")
    print(f"[out] {sel}")
    for name, t, s in manifest:
        print(f"   {name}  t={t:5.1f}s  sal={s:.3f}")


if __name__ == "__main__":
    main()
