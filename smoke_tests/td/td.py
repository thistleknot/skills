"""
Text-based tower defense game.

Grid: 10x10. Tower at center (5,5). Enemies spawn at (0,0) and move
diagonally toward (9,9). Tower attacks (removes) nearest enemy each tick.
3 waves of 3 enemies each; one new enemy spawns per tick per wave.
"""
import math, time

GRID = 10
TOWER = (5, 5)


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def print_grid(enemies, tick):
    print(f"\n--- Tick {tick} ---")
    for r in range(GRID):
        row = ""
        for c in range(GRID):
            if (r, c) == TOWER:
                row += "T "
            elif (r, c) in enemies:
                row += "E "
            else:
                row += ". "
        print(row)


def step(pos):
    r, c = pos
    dr = 1 if r < 9 else (-1 if r > 9 else 0)
    dc = 1 if c < 9 else (-1 if c > 9 else 0)
    return (r + dr, c + dc)


def run():
    enemies = set()
    tick = 0
    for wave in range(3):
        print(f"\n=== Wave {wave + 1} ===")
        spawned = 0
        while spawned < 3 or enemies:
            tick += 1
            # Spawn one enemy per tick until wave quota filled
            if spawned < 3:
                enemies.add((0, 0))
                spawned += 1
            # Tower attacks nearest enemy
            if enemies:
                target = min(enemies, key=lambda e: dist(TOWER, e))
                enemies.discard(target)
            # Move remaining enemies
            enemies = {step(e) for e in enemies}
            # Remove enemies that reached or passed destination
            enemies = {e for e in enemies if e[0] < GRID and e[1] < GRID}
            print_grid(enemies, tick)
    print("\nAll waves complete.")


if __name__ == "__main__":
    run()
