"""
Tower Defense GIF renderer — RL + chaos edition.

Imports simulate() from td.py (same folder).
Frame sequence per tick:
  1. Shot frame  (laser beam tower->target, target still present)
  2. Explosion   (starburst at kill site, type-colored, target removed)
  3. Move frame  (enemies advanced, HP bars, type labels, RL header)
"""
import math
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from td import simulate, TOWER, TOWER_RANGE, ENEMY_COLOR

from PIL import Image, ImageDraw

GRID      = 10
CELL      = 52
HEADER    = 54
W         = GRID * CELL
H         = GRID * CELL + HEADER
FPS       = 6
FRAME_MS  = 1000 // FPS
EFFECT_MS = FRAME_MS // 3

BG         = (10,  12,  24)
GRID_LINE  = (28,  32,  60)
HEADER_BG  = (18,  20,  42)
TOWER_GLOW = (0,   60,  38)
TOWER_COL  = (0,   230, 120)
TOWER_TXT  = (0,   0,   0)
TEXT_COL   = (160, 165, 210)
WAVE_COL   = (90,  200, 255)
RANGE_COL  = (0,   60,  35)
BEAM_OUTER = (255, 120, 0)
BEAM_CORE  = (255, 240, 60)


def cell_center(r, c):
    return (c * CELL + CELL // 2, r * CELL + CELL // 2 + HEADER)


def new_frame():
    img = Image.new("RGB", (W, H), BG)
    return img, ImageDraw.Draw(img)


def draw_range_ring(draw):
    tr, tc = TOWER
    cx, cy = cell_center(tr, tc)
    px = int(TOWER_RANGE * CELL)
    draw.ellipse([cx-px, cy-px, cx+px, cy+px], fill=RANGE_COL)


def draw_grid(draw):
    for i in range(GRID + 1):
        x = i * CELL
        draw.line([(x, HEADER), (x, H)],       fill=GRID_LINE, width=1)
        draw.line([(0, HEADER+i*CELL), (W, HEADER+i*CELL)], fill=GRID_LINE, width=1)


def draw_header(draw, wave, tick, q_size, reward):
    draw.rectangle([0, 0, W, HEADER-1], fill=HEADER_BG)
    draw.text((8,  8),  f"Wave {wave}   Tick {tick:02d}", fill=TEXT_COL)
    draw.text((8,  30), f"Q={q_size}   reward={reward:+.0f}", fill=WAVE_COL)
    draw.text((W-90, 8), f"Range: {TOWER_RANGE}", fill=TEXT_COL)


def draw_tower(draw):
    r, c = TOWER
    cx, cy = cell_center(r, c)
    draw.ellipse([cx-18, cy-18, cx+18, cy+18], fill=TOWER_GLOW)
    draw.rectangle([cx-12, cy-12, cx+12, cy+12], fill=TOWER_COL,
                   outline=(0,180,90), width=2)
    draw.text((cx-4, cy-7), "T", fill=TOWER_TXT)


def draw_enemies(draw, enemies):
    for e in enemies:
        r, c   = e.pos
        cx, cy = cell_center(r, c)
        col    = ENEMY_COLOR[e.etype]
        pad    = 11
        # glow ring (darker tint of color)
        gc = tuple(max(0, v//3) for v in col)
        draw.ellipse([cx-pad-3, cy-pad-3, cx+pad+3, cy+pad+3], fill=gc)
        # body
        draw.ellipse([cx-pad, cy-pad, cx+pad, cy+pad], fill=col)
        # type label
        draw.text((cx-4, cy-14), e.etype.value, fill=(255,255,255))
        # HP bar (below circle, proportional)
        bar_w  = 2*pad
        bar_h  = 4
        bar_x  = cx - pad
        bar_y  = cy + pad + 2
        ratio  = e.hp / max(e.max_hp, 1)
        draw.rectangle([bar_x, bar_y, bar_x+bar_w, bar_y+bar_h], fill=(40,40,40))
        draw.rectangle([bar_x, bar_y, bar_x+int(bar_w*ratio), bar_y+bar_h], fill=(0,220,80))


def draw_beam(draw, target):
    tr, tc = TOWER
    tcx, tcy = cell_center(tr, tc)
    ecx, ecy = cell_center(*target.pos)
    draw.line([(tcx,tcy),(ecx,ecy)], fill=BEAM_OUTER, width=7)
    draw.line([(tcx,tcy),(ecx,ecy)], fill=BEAM_CORE,  width=2)
    draw.ellipse([tcx-6, tcy-6, tcx+6, tcy+6], fill=BEAM_CORE)


def draw_explosion(draw, target):
    r, c   = target.pos
    cx, cy = cell_center(r, c)
    col    = ENEMY_COLOR[target.etype]
    for angle in range(0, 360, 30):
        rad    = math.radians(angle)
        length = 22 if angle % 60 == 0 else 14
        ex = cx + int(length * math.cos(rad))
        ey = cy + int(length * math.sin(rad))
        draw.line([(cx,cy),(ex,ey)], fill=col, width=3)
    draw.ellipse([cx-9, cy-9, cx+9, cy+9], fill=(255,240,80))


def make_frame(wave, tick, enemies, q_size, reward, killed=None, mode="move"):
    img, draw = new_frame()
    draw_range_ring(draw)
    draw_grid(draw)
    draw_header(draw, wave, tick, q_size, reward)
    draw_tower(draw)
    draw_enemies(draw, enemies)
    if mode == "shot" and killed:
        draw_beam(draw, killed)
    if mode == "expl" and killed:
        draw_explosion(draw, killed)
    return img


def build_gif(out_path):
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    ticks = simulate()
    images, durations = [], []

    for td in ticks:
        q  = td["q_size"]
        rw = td["last_reward"]
        kl = td["killed"]

        if kl:
            images.append(make_frame(td["wave"], td["tick"],
                                     td["enemies_pre"], q, rw, kl, mode="shot"))
            durations.append(EFFECT_MS)
            images.append(make_frame(td["wave"], td["tick"],
                                     td["enemies_post_kill"], q, rw, kl, mode="expl"))
            durations.append(EFFECT_MS)

        images.append(make_frame(td["wave"], td["tick"],
                                 td["enemies_final"], q, rw, mode="move"))
        durations.append(FRAME_MS)

    images[0].save(
        out_path,
        save_all=True, append_images=images[1:],
        duration=durations, loop=0, optimize=False,
    )
    print(f"Saved -> {out_path}  ({len(images)} frames, {len(ticks)} ticks)")


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "td.gif")
    build_gif(out)
