from __future__ import annotations

import math
import random
from typing import List, Tuple

Grid = List[List[float]]
Coord = Tuple[int, int]


def make_base_heightmap(width: int, height: int, seed: int | None = None) -> Grid:
    if seed is not None:
        random.seed(seed)

    grid: Grid = [[50.0 for _ in range(width)] for _ in range(height)]

    # rende il centro più continentale e i bordi leggermente più bassi
    _apply_continental_mask(grid, width, height)

    _add_mountain_ranges(grid, width, height)
    _add_hills(grid, width, height)

    # meno bacini rispetto a prima
    _add_basins(grid, width, height)

    _add_noise(grid, width, height)

    blur(grid, passes=3)
    normalize(grid)

    return grid


def _apply_continental_mask(grid: Grid, width: int, height: int) -> None:
    cx = width / 2
    cy = height / 2
    max_dist = math.sqrt(cx * cx + cy * cy)

    for y in range(height):
        for x in range(width):
            dx = x - cx
            dy = y - cy
            dist = math.sqrt(dx * dx + dy * dy)
            t = min(1.0, dist / max_dist)  # 0 centro, 1 bordo

            # Keep a strong mainland in the center while preserving irregular coastlines.
            angle = math.atan2(dy, dx)
            waviness = (
                math.sin(angle * 3.0) * 0.06
                + math.cos(angle * 5.0) * 0.04
            )
            warped_t = max(0.0, min(1.0, t + waviness))

            center_boost = (1.0 - warped_t) ** 1.35
            edge_drop = warped_t ** 1.10
            grid[y][x] += center_boost * 18.0
            grid[y][x] -= edge_drop * 10.5


def _add_mountain_ranges(grid: Grid, width: int, height: int) -> None:
    num_ranges = random.randint(2, 4)

    for _ in range(num_ranges):
        x = random.randint(width // 8, width - width // 8 - 1)
        y = random.randint(height // 8, height - height // 8 - 1)

        length = random.randint(max(12, width // 8), max(20, width // 4))
        dx = random.choice([-1, 0, 1])
        dy = random.choice([-1, 0, 1])

        if dx == 0 and dy == 0:
            dx = 1

        for _step in range(length):
            radius = random.randint(2, 4)
            raise_area(grid, x, y, radius=radius, amount=random.uniform(16, 24))

            if random.random() < 0.35:
                dx += random.choice([-1, 0, 1])
                dy += random.choice([-1, 0, 1])
                dx = max(-1, min(1, dx))
                dy = max(-1, min(1, dy))
                if dx == 0 and dy == 0:
                    dx = random.choice([-1, 1])

            x += dx
            y += dy

            x = max(2, min(width - 3, x))
            y = max(2, min(height - 3, y))


def _add_hills(grid: Grid, width: int, height: int) -> None:
    for _ in range(random.randint(8, 14)):
        x = random.randint(0, width - 1)
        y = random.randint(0, height - 1)
        raise_area(
            grid,
            x,
            y,
            radius=random.randint(3, 7),
            amount=random.uniform(5, 10),
        )


def _add_basins(grid: Grid, width: int, height: int) -> None:
    # Fewer and softer basins to reduce terrain fragmentation.
    for _ in range(random.randint(0, 2)):
        x = random.randint(width // 6, width - width // 6 - 1)
        y = random.randint(height // 6, height - height // 6 - 1)
        lower_area(
            grid,
            x,
            y,
            radius=random.randint(3, 5),
            amount=random.uniform(5, 10),
        )


def _add_noise(grid: Grid, width: int, height: int) -> None:
    for y in range(height):
        for x in range(width):
            grid[y][x] += random.uniform(-2.0, 2.0)


def raise_area(grid: Grid, cx: int, cy: int, radius: int, amount: float) -> None:
    h = len(grid)
    w = len(grid[0])

    for y in range(max(0, cy - radius), min(h, cy + radius + 1)):
        for x in range(max(0, cx - radius), min(w, cx + radius + 1)):
            dist = abs(x - cx) + abs(y - cy)
            if dist <= radius:
                factor = 1.0 - (dist / max(1, radius + 1))
                grid[y][x] += amount * factor


def lower_area(grid: Grid, cx: int, cy: int, radius: int, amount: float) -> None:
    h = len(grid)
    w = len(grid[0])

    for y in range(max(0, cy - radius), min(h, cy + radius + 1)):
        for x in range(max(0, cx - radius), min(w, cx + radius + 1)):
            dist = abs(x - cx) + abs(y - cy)
            if dist <= radius:
                factor = 1.0 - (dist / max(1, radius + 1))
                grid[y][x] -= amount * factor


def blur(grid: Grid, passes: int = 1) -> None:
    h = len(grid)
    w = len(grid[0])

    for _ in range(passes):
        new_grid = [[grid[y][x] for x in range(w)] for y in range(h)]

        for y in range(h):
            for x in range(w):
                vals = []
                for oy in (-1, 0, 1):
                    for ox in (-1, 0, 1):
                        ny = y + oy
                        nx = x + ox
                        if 0 <= nx < w and 0 <= ny < h:
                            vals.append(grid[ny][nx])
                new_grid[y][x] = sum(vals) / len(vals)

        for y in range(h):
            for x in range(w):
                grid[y][x] = new_grid[y][x]


def normalize(grid: Grid) -> None:
    vals = [v for row in grid for v in row]
    min_v = min(vals)
    max_v = max(vals)

    if max_v - min_v < 1e-6:
        return

    for y in range(len(grid)):
        for x in range(len(grid[0])):
            grid[y][x] = ((grid[y][x] - min_v) / (max_v - min_v)) * 100.0
