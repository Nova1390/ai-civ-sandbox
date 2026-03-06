from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Tuple

from config import HOUSE_WOOD_COST, HOUSE_STONE_COST

if TYPE_CHECKING:
    from world import World
    from agent import Agent


Coord = Tuple[int, int]

STORAGE_WOOD_COST = 4
STORAGE_STONE_COST = 2


def building_score(world: "World", x: int, y: int) -> int:
    score = 0

    for dx in range(-2, 3):
        for dy in range(-2, 3):
            nx = x + dx
            ny = y + dy
            if (nx, ny) in world.structures:
                score += 5

    for dx in range(-3, 4):
        for dy in range(-3, 4):
            nx = x + dx
            ny = y + dy
            if 0 <= nx < world.width and 0 <= ny < world.height:
                if world.tiles[ny][nx] == "F":
                    score += 1

    return score


def count_nearby_houses(world: "World", x: int, y: int, radius: int = 5) -> int:
    count = 0
    for hx, hy in world.structures:
        if abs(hx - x) <= radius and abs(hy - y) <= radius:
            count += 1
    return count


def count_nearby_population(world: "World", x: int, y: int, radius: int = 6) -> int:
    count = 0
    for a in world.agents:
        if not a.alive:
            continue
        if abs(a.x - x) <= radius and abs(a.y - y) <= radius:
            count += 1
    return count


def can_build_at(world: "World", x: int, y: int) -> bool:
    if not world.is_walkable(x, y):
        return False
    if (x, y) in world.structures:
        return False
    if (x, y) in getattr(world, "storage_buildings", set()):
        return False
    return True


def try_build_house(world: "World", agent: "Agent") -> bool:
    if len(world.structures) >= world.MAX_STRUCTURES:
        return False

    if (
        agent.inventory.get("wood", 0) < HOUSE_WOOD_COST
        or agent.inventory.get("stone", 0) < HOUSE_STONE_COST
    ):
        return False

    best_pos: Optional[Coord] = None
    best_score = -10**9

    for dx in range(-3, 4):
        for dy in range(-3, 4):
            x = agent.x + dx
            y = agent.y + dy

            if not can_build_at(world, x, y):
                continue

            nearby_houses = count_nearby_houses(world, x, y, radius=5)
            nearby_population = count_nearby_population(world, x, y, radius=6)

            if nearby_houses >= world.MAX_HOUSES_PER_VILLAGE:
                continue

            allowed_houses = nearby_population // 2 + 1
            if nearby_houses >= allowed_houses:
                continue

            if nearby_houses == 0 and len(world.structures) >= world.MAX_NEW_VILLAGE_SEEDS:
                continue

            score = building_score(world, x, y)

            if nearby_houses == 0:
                score -= 10

            if score > best_score:
                best_score = score
                best_pos = (x, y)

    if best_pos is None:
        return False

    bx, by = best_pos
    world.structures.add((bx, by))
    agent.inventory["wood"] -= HOUSE_WOOD_COST
    agent.inventory["stone"] -= HOUSE_STONE_COST
    return True


def try_build_storage(world: "World", agent: "Agent") -> bool:
    village_id = getattr(agent, "village_id", None)
    village = world.get_village_by_id(village_id)
    if village is None:
        return False

    storage_pos = village.get("storage_pos")
    if not storage_pos:
        return False

    sx = storage_pos["x"]
    sy = storage_pos["y"]

    if (sx, sy) in getattr(world, "storage_buildings", set()):
        return False

    if (
        agent.inventory.get("wood", 0) < STORAGE_WOOD_COST
        or agent.inventory.get("stone", 0) < STORAGE_STONE_COST
    ):
        return False

    if abs(agent.x - sx) > 2 or abs(agent.y - sy) > 2:
        return False

    if not can_build_at(world, sx, sy):
        return False

    world.storage_buildings.add((sx, sy))
    agent.inventory["wood"] -= STORAGE_WOOD_COST
    agent.inventory["stone"] -= STORAGE_STONE_COST
    return True