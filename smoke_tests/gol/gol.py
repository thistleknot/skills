import random

def create_grid(size, seed=None):
    if seed is not None:
        random.seed(seed)
    return [[random.choice([True, False]) for _ in range(size)] for _ in range(size)]

def print_grid(grid):
    for row in grid:
        print("".join(["#" if cell else "." for cell in row]))
    print()

def get_neighbors(grid, r, c, size):
    neighbors = 0
    for dr in [-1, 0, 1]:
        for dc in [-1, 0, 1]:
            if dr == 0 and dc == 0:
                continue
            nr, nc = (r + dr) % size, (c + dc) % size
            if grid[nr][nc]:
                neighbors += 1
    return neighbors

def next_generation(grid, size):
    new_grid = [[False for _ in range(size)] for _ in range(size)]
    for r in range(size):
        for c in range(size):
            neighbors = get_neighbors(grid, r, c, size)
            if grid[r][c]:
                if neighbors in [2, 3]:
                    new_grid[r][c] = True
            else:
                if neighbors == 3:
                    new_grid[r][c] = True
    return new_grid

def main():
    size = 20
    grid = create_grid(size)
    for _ in range(5):
        print_grid(grid)
        grid = next_generation(grid, size)

if __name__ == "__main__":
    main()
