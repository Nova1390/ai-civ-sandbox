from __future__ import annotations

from collections import deque
from typing import List, Set, Tuple

TileGrid = List[List[str]]
Coord = Tuple[int, int]


def smooth_tiles(tiles: TileGrid, passes: int = 2) -> TileGrid:
    h = len(tiles)
    w = len(tiles[0])

    for _ in range(passes):
        new_tiles = [[tiles[y][x] for x in range(w)] for y in range(h)]

        for y in range(h):
            for x in range(w):
                counts: dict[str, int] = {}

                for oy in (-1, 0, 1):
                    for ox in (-1, 0, 1):
                        nx = x + ox
                        ny = y + oy
                        if 0 <= nx < w and 0 <= ny < h:
                            t = tiles[ny][nx]
                            counts[t] = counts.get(t, 0) + 1

                current = tiles[y][x]
                best_tile = max(counts, key=counts.get)

                if counts.get(best_tile, 0) >= 5:
                    new_tiles[y][x] = best_tile
                else:
                    new_tiles[y][x] = current

        tiles = new_tiles

    return tiles


def remove_small_water_bodies(tiles: TileGrid, min_size: int = 18) -> TileGrid:
    h = len(tiles)
    w = len(tiles[0])

    visited: Set[Coord] = set()

    for y in range(h):
        for x in range(w):
            if tiles[y][x] != "W" or (x, y) in visited:
                continue

            component = []
            q = deque([(x, y)])
            visited.add((x, y))

            while q:
                cx, cy = q.popleft()
                component.append((cx, cy))

                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < w and 0 <= ny < h:
                        if tiles[ny][nx] == "W" and (nx, ny) not in visited:
                            visited.add((nx, ny))
                            q.append((nx, ny))

            if len(component) < min_size:
                for cx, cy in component:
                    tiles[cy][cx] = "G"

    return tiles


def collapse_hills_to_grass_for_runtime(tiles: TileGrid) -> TileGrid:
    """
    Manteniamo le colline in worldgen, ma se il runtime attuale usa solo
    G/F/M/W allora convertiamo H -> G.
    """
    h = len(tiles)
    w = len(tiles[0])

    out = [[tiles[y][x] for x in range(w)] for y in range(h)]

    for y in range(h):
        for x in range(w):
            if out[y][x] == "H":
                out[y][x] = "G"

    return out


def land_ratio(tiles: TileGrid) -> float:
    h = len(tiles)
    w = len(tiles[0])
    land = 0

    for y in range(h):
        for x in range(w):
            if tiles[y][x] != "W":
                land += 1

    return land / max(1, w * h)


def largest_land_component_ratio(tiles: TileGrid) -> float:
    h = len(tiles)
    w = len(tiles[0])
    visited: Set[Coord] = set()

    largest = 0
    land_total = 0

    for y in range(h):
        for x in range(w):
            if tiles[y][x] == "W":
                continue
            land_total += 1

            if (x, y) in visited:
                continue

            size = 0
            q = deque([(x, y)])
            visited.add((x, y))

            while q:
                cx, cy = q.popleft()
                size += 1

                for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if 0 <= nx < w and 0 <= ny < h:
                        if tiles[ny][nx] != "W" and (nx, ny) not in visited:
                            visited.add((nx, ny))
                            q.append((nx, ny))

            if size > largest:
                largest = size

    if land_total == 0:
        return 0.0

    return largest / land_total
