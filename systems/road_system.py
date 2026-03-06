from __future__ import annotations

ROAD_BUILD_THRESHOLD = 12


def record_agent_step(world, x: int, y: int) -> None:
    pos = (x, y)
    world.road_usage[pos] = world.road_usage.get(pos, 0) + 1

    if world.road_usage[pos] >= ROAD_BUILD_THRESHOLD:
        if pos not in world.roads and pos not in world.structures:
            world.roads.add(pos)