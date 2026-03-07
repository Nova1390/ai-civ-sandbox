from __future__ import annotations

import random
from typing import List, Set, Tuple

Grid = List[List[float]]
TileGrid = List[List[str]]
Coord = Tuple[int, int]


def assign_base_tiles(heightmap: Grid, rivers: Set[Coord]) -> TileGrid:
    h = len(heightmap)
    w = len(heightmap[0])

    tiles: TileGrid = [["G" for _ in range(w)] for _ in range(h)]

    for y in range(h):
        for x in range(w):
            v = heightmap[y][x]

            if (x, y) in rivers:
                tiles[y][x] = "W"
            elif v <= 8:
                tiles[y][x] = "W"      # laghi più rari
            elif v <= 42:
                tiles[y][x] = "G"      # pianure basse
            elif v <= 62:
                tiles[y][x] = "H"      # colline
            else:
                tiles[y][x] = "M"      # montagne

    grow_forests(tiles, heightmap)
    return tiles


def grow_forests(tiles: TileGrid, heightmap: Grid) -> None:
    h = len(tiles)
    w = len(tiles[0])

    seeds: list[Coord] = []
    for _ in range(max(6, w // 10)):
        x = random.randint(0, w - 1)
        y = random.randint(0, h - 1)

        if tiles[y][x] in ("G", "H") and 20 <= heightmap[y][x] <= 65:
            seeds.append((x, y))

    for sx, sy in seeds:
        _expand_forest(tiles, sx, sy, size=random.randint(10, 28))


def _expand_forest(tiles: TileGrid, sx: int, sy: int, size: int) -> None:
    h = len(tiles)
    w = len(tiles[0])

    frontier = [(sx, sy)]
    seen: Set[Coord] = set()

    while frontier and len(seen) < size:
        x, y = frontier.pop(0)
        if (x, y) in seen:
            continue
        seen.add((x, y))

        if tiles[y][x] in ("G", "H"):
            tiles[y][x] = "F"

        neighbors = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
        random.shuffle(neighbors)

        for nx, ny in neighbors:
            if 0 <= nx < w and 0 <= ny < h:
                if tiles[ny][nx] in ("G", "H") and random.random() < 0.75:
                    frontier.append((nx, ny))
