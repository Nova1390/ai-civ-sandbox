from __future__ import annotations

from agent import Agent
from brain import FoodBrain
import systems.farming_system as farming_system
from world import World


def _farm_world() -> World:
    world = World(width=24, height=24, num_agents=0, seed=42, llm_enabled=False)
    world.tiles = [["G" for _ in range(world.width)] for _ in range(world.height)]
    world.food = set()
    world.wood = set()
    world.stone = set()
    world.farms = set()
    world.farm_plots = {}
    world.buildings = {}
    world.structures = set()
    world.storage_buildings = set()
    world.building_occupancy = {}
    world.camps = {}
    world.villages = [
        {
            "id": 1,
            "village_uid": "v-000001",
            "center": {"x": 10, "y": 10},
            "farm_zone_center": {"x": 10, "y": 10},
            "population": 8,
            "houses": 3,
            "storage": {"food": 0, "wood": 0, "stone": 0},
            "needs": {"food_low": True},
        }
    ]
    return world


def test_farm_site_requires_productivity_observations_before_creation() -> None:
    world = _farm_world()
    world.villages[0]["needs"] = {"food_low": False}
    world.camps["c-1"] = {"camp_id": "c-1", "x": 10, "y": 10, "active": True, "food_cache": 0}
    farmer = Agent(x=10, y=10, brain=None, is_player=False, player_id=None)
    farmer.village_id = 1
    farmer.role = "farmer"
    farmer.inventory["wood"] = 2

    assert world.try_build_farm(farmer) is False

    world.villages[0]["needs"] = {"food_low": True}
    for _ in range(3):
        world.record_farm_discovery_observation(10, 10, success=True, amount=1)
    assert world.try_build_farm(farmer) is True

    snap = world.compute_settlement_progression_snapshot()
    assert int(snap["farm_sites_created"]) >= 1


def test_farmer_prefers_returning_to_known_farm_target() -> None:
    world = _farm_world()
    world.farms.add((12, 10))
    world.farm_plots[(12, 10)] = {"x": 12, "y": 10, "state": "prepared", "growth": 0, "village_id": 1}
    farmer = Agent(x=8, y=10, brain=FoodBrain(), is_player=False, player_id=None)
    farmer.village_id = 1
    farmer.role = "farmer"
    farmer.task = "farm_cycle"

    t1 = farmer.brain.find_farm_target(farmer, world, prefer_ripe=False)
    assert t1 == (12, 10)
    farmer.x = 9
    t2 = farmer.brain.find_farm_target(farmer, world, prefer_ripe=False)
    assert t2 == (12, 10)


def test_farm_can_be_abandoned_after_long_idle_low_productivity() -> None:
    world = _farm_world()
    world.farms.add((10, 10))
    world.farm_plots[(10, 10)] = {
        "x": 10,
        "y": 10,
        "state": "prepared",
        "growth": 0,
        "village_id": 1,
        "last_work_tick": 0,
        "productivity_score": 0.1,
    }
    world.tick = 400
    farming_system.update_farms(world)
    assert (10, 10) not in world.farm_plots
    snap = world.compute_settlement_progression_snapshot()
    assert int(snap["farm_abandoned"]) >= 1


def test_survival_override_still_beats_farming_under_true_crisis() -> None:
    world = _farm_world()
    world.food.add((10, 11))
    world.farms.add((11, 10))
    world.farm_plots[(11, 10)] = {"x": 11, "y": 10, "state": "prepared", "growth": 0, "village_id": 1}

    farmer = Agent(x=10, y=10, brain=FoodBrain(), is_player=False, player_id=None)
    farmer.village_id = 1
    farmer.role = "farmer"
    farmer.task = "farm_cycle"
    farmer.hunger = 10

    action = farmer.brain.decide(farmer, world)
    assert action[0] == "move"
    assert (farmer.x + int(action[1]), farmer.y + int(action[2])) == (10, 11)


def test_settlement_snapshot_exports_farm_emergence_metrics() -> None:
    world = _farm_world()
    world.farms.add((10, 10))
    world.farm_plots[(10, 10)] = {
        "x": 10,
        "y": 10,
        "state": "prepared",
        "growth": 0,
        "village_id": 1,
        "last_work_tick": 0,
        "productivity_score": 1.2,
    }
    farmer = Agent(x=10, y=10, brain=None, is_player=False, player_id=None)
    farmer.village_id = 1
    farmer.role = "farmer"
    farmer.task = "farm_cycle"
    world.agents = [farmer]

    world.update_settlement_progression_metrics()
    snap = world.compute_settlement_progression_snapshot()
    for key in (
        "farm_sites_created",
        "farm_work_events",
        "farm_abandoned",
        "farm_yield_events",
        "farm_productivity_score_avg",
        "agents_farming_count",
        "farm_candidate_detected_count",
        "farm_candidate_bootstrap_trigger_count",
        "farm_candidate_rejected_count",
        "early_farm_loop_persistence_ticks",
        "early_farm_loop_abandonment_count",
        "first_harvest_after_farm_creation_count",
    ):
        assert key in snap
    assert float(snap["farm_productivity_score_avg"]) > 0.0
    assert int(snap["agents_farming_count"]) >= 1


def test_house_cluster_and_repeat_observation_can_unlock_candidate_without_camp() -> None:
    world = _farm_world()
    world.camps = {}
    world.villages[0]["houses"] = 3
    world.villages[0]["needs"] = {"food_low": False}
    farmer = Agent(x=10, y=10, brain=None, is_player=False, player_id=None)
    farmer.village_id = 1
    farmer.role = "farmer"
    farmer.inventory["wood"] = 1
    for _ in range(2):
        world.record_farm_discovery_observation(10, 10, success=True, amount=1)
    assert world.try_build_farm(farmer) is True


def test_bootstrap_trigger_metric_records_fragile_viable_first_farm() -> None:
    world = _farm_world()
    world.camps = {"c-1": {"camp_id": "c-1", "x": 10, "y": 10, "active": True, "food_cache": 0}}
    world.villages[0]["houses"] = 1
    world.villages[0]["needs"] = {"food_low": True}
    farmer = Agent(x=10, y=10, brain=None, is_player=False, player_id=None)
    farmer.village_id = 1
    farmer.role = "farmer"
    farmer.hunger = 60.0
    farmer.inventory["wood"] = 1
    world.record_farm_discovery_observation(10, 10, success=False, amount=0)
    assert world.try_build_farm(farmer) is True
    snap = world.compute_settlement_progression_snapshot()
    assert int(snap["farm_candidate_bootstrap_trigger_count"]) >= 1


def test_early_productive_farm_loop_persistence_ticks_increase() -> None:
    world = _farm_world()
    world.farms.add((10, 10))
    world.farm_plots[(10, 10)] = {
        "x": 10,
        "y": 10,
        "state": "ripe",
        "growth": 0,
        "village_id": 1,
        "created_tick": 1,
        "last_work_tick": 1,
        "productivity_score": 0.95,
        "yield_events": 0,
    }
    world.tick = 50
    farmer = Agent(x=10, y=10, brain=None, is_player=False, player_id=None)
    farmer.village_id = 1
    farmer.role = "farmer"
    farmer.inventory["food"] = 0
    world.work_farm(farmer)
    snap = world.compute_settlement_progression_snapshot()
    assert int(snap["early_farm_loop_persistence_ticks"]) >= 1
    assert int(snap["first_harvest_after_farm_creation_count"]) >= 1
