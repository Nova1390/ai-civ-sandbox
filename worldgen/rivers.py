from __future__ import annotations

import random
from typing import List, Set, Tuple

Grid = List[List[float]]
Coord = Tuple[int, int]


def carve_rivers(heightmap: Grid, num_rivers: int | None = None) -> Set[Coord]:
    h = len(heightmap)
    w = len(heightmap[0])

    if num_rivers is None:
        num_rivers = max(2, min(6, w // 25))

    candidates: list[Coord] = []
    for y in range(h):
        for x in range(w):
            if heightmap[y][x] >= 72:
                candidates.append((x, y))

    random.shuffle(candidates)

    rivers: Set[Coord] = set()
    used_sources: Set[Coord] = set()
    created = 0

    for source in candidates:
        if created >= num_rivers:
            break

        if source in used_sources:
            continue

        path = _trace_river(heightmap, source)
        if len(path) >= 10:
            rivers.update(path)
            used_sources.add(source)
            created += 1

    return rivers


def _trace_river(heightmap: Grid, source: Coord) -> list[Coord]:
    h = len(heightmap)
    w = len(heightmap[0])

    x, y = source
    path: list[Coord] = []
    visited: Set[Coord] = set()

    for _ in range((w + h) * 2):
        pos = (x, y)
        path.append(pos)
        visited.add(pos)

        if x == 0 or y == 0 or x == w - 1 or y == h - 1:
            break

        if heightmap[y][x] <= 20:
            break

        next_pos = None
        best_val = heightmap[y][x]

        neighbors = [
            (x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1),
            (x + 1, y + 1), (x - 1, y - 1), (x + 1, y - 1), (x - 1, y + 1),
        ]
        random.shuffle(neighbors)

        for nx, ny in neighbors:
            if not (0 <= nx < w and 0 <= ny < h):
                continue
            if (nx, ny) in visited:
                continue

            val = heightmap[ny][nx]
            if val < best_val:
                best_val = val
                next_pos = (nx, ny)

        if next_pos is None:
            lower_neighbors = []
            for nx, ny in neighbors:
                if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in visited:
                    lower_neighbors.append((heightmap[ny][nx], nx, ny))

            if not lower_neighbors:
                break

            lower_neighbors.sort(key=lambda t: t[0])
            _, nx, ny = lower_neighbors[0]
            next_pos = (nx, ny)

        x, y = next_pos

    return path