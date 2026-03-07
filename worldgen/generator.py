from __future__ import annotations

from typing import List

from .heightmap import make_base_heightmap
from .rivers import carve_rivers
from .biomes import assign_base_tiles
from .smoothing import (
    smooth_tiles,
    remove_small_water_bodies,
    collapse_hills_to_grass_for_runtime,
    land_ratio,
    largest_land_component_ratio,
)

TileGrid = List[List[str]]

TARGET_LAND_RATIO = 0.72
MIN_MAINLAND_RATIO = 0.68
MAX_WORLDGEN_ATTEMPTS = 10


def generate_world(width: int, height: int) -> TileGrid:
    best_tiles: TileGrid | None = None
    best_score = -1.0

    for _ in range(MAX_WORLDGEN_ATTEMPTS):
        heightmap = make_base_heightmap(width, height)
        rivers = carve_rivers(heightmap)
        tiles = assign_base_tiles(heightmap, rivers)
        tiles = smooth_tiles(tiles, passes=3)
        tiles = remove_small_water_bodies(tiles, min_size=28)
        tiles = collapse_hills_to_grass_for_runtime(tiles)

        lr = land_ratio(tiles)
        main = largest_land_component_ratio(tiles)

        if lr >= TARGET_LAND_RATIO and main >= MIN_MAINLAND_RATIO:
            return tiles

        # Keep the best fallback, preferring high land ratio and strong mainland continuity.
        score = (lr * 0.65) + (main * 0.35)
        if score > best_score:
            best_score = score
            best_tiles = tiles

    if best_tiles is not None:
        return best_tiles

    # Defensive fallback, should never happen in practice.
    heightmap = make_base_heightmap(width, height)
    rivers = carve_rivers(heightmap)
    tiles = assign_base_tiles(heightmap, rivers)
    tiles = smooth_tiles(tiles, passes=3)
    tiles = remove_small_water_bodies(tiles, min_size=28)
    return collapse_hills_to_grass_for_runtime(tiles)
