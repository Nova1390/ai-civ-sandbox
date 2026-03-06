from __future__ import annotations

from typing import Tuple

Coord = Tuple[int, int]

PREPARE_WOOD_COST = 1
PLANT_GROW_TICKS = 35
HARVEST_YIELD = 1


def update_farms(world) -> None:
    to_delete = []

    for pos, plot in world.farm_plots.items():
        state = plot.get("state", "prepared")

        if state == "planted":
            plot["state"] = "growing"
            plot["growth"] = 1
            continue

        if state == "growing":
            plot["growth"] = plot.get("growth", 0) + 1
            if plot["growth"] >= PLANT_GROW_TICKS:
                plot["state"] = "ripe"
            continue

        if state == "dead":
            to_delete.append(pos)

    for pos in to_delete:
        world.farm_plots.pop(pos, None)
        world.farms.discard(pos)


def try_build_farm(world, agent) -> bool:
    if agent.inventory.get("wood", 0) < PREPARE_WOOD_COST:
        return False

    village_id = getattr(agent, "village_id", None)
    village = world.get_village_by_id(village_id)
    if village is None:
        return False

    x = agent.x
    y = agent.y
    pos = (x, y)

    if world.tiles[y][x] != "G":
        return False

    if pos in world.structures:
        return False

    if pos in world.farms or pos in world.farm_plots:
        return False

    # non attaccato alle case
    for sx, sy in world.structures:
        if abs(sx - x) <= 1 and abs(sy - y) <= 1:
            return False

    same_village_farms = [
        p for p, plot in world.farm_plots.items()
        if plot.get("village_id") == village_id
    ]

    # limite campi per villaggio
    max_farms_for_village = max(2, village["population"] // 2 + village["houses"])
    if len(same_village_farms) >= max_farms_for_village:
        return False

    farm_zone = village.get("farm_zone_center", village["center"])
    fzx = farm_zone["x"]
    fzy = farm_zone["y"]

    if not same_village_farms:
        # primo campo: vicino al centro agricolo del villaggio
        if abs(fzx - x) > 3 or abs(fzy - y) > 3:
            return False
    else:
        # campi successivi: cluster vicino ai campi esistenti
        adjacent_same_village = False
        for fx, fy in same_village_farms:
            if abs(fx - x) <= 1 and abs(fy - y) <= 1:
                adjacent_same_village = True
                break

        if not adjacent_same_village:
            return False

        # non allargare troppo il cluster
        if abs(fzx - x) > 6 or abs(fzy - y) > 6:
            return False

    world.farms.add(pos)
    world.farm_plots[pos] = {
        "x": x,
        "y": y,
        "state": "prepared",
        "growth": 0,
        "village_id": village_id,
        "owner_role": getattr(agent, "role", "npc"),
    }

    agent.inventory["wood"] -= PREPARE_WOOD_COST
    return True


def work_farm(world, agent) -> bool:
    pos = (agent.x, agent.y)
    plot = world.farm_plots.get(pos)

    if not plot:
        return False

    state = plot.get("state", "prepared")
    village_id = plot.get("village_id")
    village = world.get_village_by_id(village_id)

    if state == "prepared":
        plot["state"] = "planted"
        plot["growth"] = 0
        return True

    if state == "ripe":
        if village is not None:
            village["storage"]["food"] = village["storage"].get("food", 0) + HARVEST_YIELD
        else:
            agent.inventory["food"] = agent.inventory.get("food", 0) + HARVEST_YIELD

        plot["state"] = "prepared"
        plot["growth"] = 0
        return True

    return False