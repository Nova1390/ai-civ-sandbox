from __future__ import annotations

from agent import Agent
from brain import FoodBrain
import systems.building_system as building_system
import systems.road_system as road_system
from world import World


def _flat_world() -> World:
    world = World(width=32, height=32, num_agents=0, seed=404, llm_enabled=False)
    world.tiles = [["G" for _ in range(world.width)] for _ in range(world.height)]
    world.agents = []
    world.villages = []
    world.structures = set()
    world.storage_buildings = set()
    world.buildings = {}
    world.building_occupancy = {}
    world.roads = set()
    world.transport_tiles = {}
    world.food = set()
    world.wood = set()
    world.stone = set()
    world.camps = {}
    return world


def _village(pop: int = 8, houses: int = 4) -> dict:
    return {
        "id": 1,
        "village_uid": "v-000001",
        "center": {"x": 10, "y": 10},
        "houses": houses,
        "population": pop,
        "storage": {"food": 10, "wood": 0, "stone": 0},
        "storage_pos": {"x": 10, "y": 10},
        "farm_zone_center": {"x": 12, "y": 10},
        "tier": 1,
    }


def test_builder_holds_position_on_site_during_build_house_task() -> None:
    world = _flat_world()
    village = _village()
    world.villages = [village]
    site = building_system.place_building(
        world,
        "house",
        (10, 10),
        village_id=1,
        village_uid="v-000001",
        operational_state="under_construction",
        construction_request={
            "wood_needed": 3,
            "stone_needed": 1,
            "food_needed": 0,
            "wood_reserved": 0,
            "stone_reserved": 0,
            "food_reserved": 0,
        },
        construction_buffer={"wood": 3, "stone": 1, "food": 0},
        construction_progress=0,
        construction_required_work=2,
    )
    assert site is not None
    builder = Agent(x=10, y=10, brain=FoodBrain(), is_player=False, player_id=None)
    builder.role = "npc"
    builder.village_id = 1
    builder.task = "build_house"
    world.agents = [builder]

    action = builder.brain.decide(builder, world)
    assert action in (None, ("wait",))


def test_construction_progress_blocked_when_builder_offsite() -> None:
    world = _flat_world()
    village = _village()
    world.villages = [village]
    site = building_system.place_building(
        world,
        "house",
        (10, 10),
        village_id=1,
        village_uid="v-000001",
        operational_state="under_construction",
        construction_request={
            "wood_needed": 3,
            "stone_needed": 1,
            "food_needed": 0,
            "wood_reserved": 0,
            "stone_reserved": 0,
            "food_reserved": 0,
        },
        construction_buffer={"wood": 3, "stone": 1, "food": 0},
        construction_progress=0,
        construction_required_work=2,
    )
    assert site is not None
    builder = Agent(x=2, y=2, brain=FoodBrain(), is_player=False, player_id=None)
    builder.role = "forager"
    builder.village_id = 1
    world.agents = [builder]

    progressed = building_system.try_build_house(world, builder)
    assert progressed is False
    updated = world.buildings[str(site["building_id"])]
    assert int(updated.get("construction_progress", 0)) == 0
    situated = world.compute_situated_construction_snapshot()
    assert int(situated["construction_offsite_blocked_ticks"]) >= 1


def test_situated_construction_records_survival_interrupt() -> None:
    world = _flat_world()
    village = _village()
    world.villages = [village]
    builder = Agent(x=10, y=10, brain=FoodBrain(), is_player=False, player_id=None)
    builder.role = "npc"
    builder.village_id = 1
    builder.task = "build_house"
    builder.hunger = 10.0
    world.agents = [builder]

    builder.update(world)
    situated = world.compute_situated_construction_snapshot()
    assert int(situated["construction_interrupted_survival"]) >= 1


def test_road_growth_suppressed_without_local_purpose() -> None:
    world = _flat_world()
    village = _village(pop=1, houses=1)
    world.villages = [village]
    house = world.place_building("house", 14, 10, village_id=1, village_uid="v-000001")
    assert house is not None
    world.should_defer_road_growth_for_village = lambda _v: (False, "")  # type: ignore[assignment]

    road_system.update_road_infrastructure(world)
    assert len(world.roads) == 0
    progression = world.compute_progression_snapshot()
    assert int(progression["road_build_suppressed_no_purpose"]) >= 1


def test_road_growth_records_purpose_when_connecting_useful_endpoints() -> None:
    world = _flat_world()
    village = _village(pop=8, houses=4)
    world.villages = [village]
    world.farm_plots[(11, 10)] = {"x": 11, "y": 10, "village_id": 1}
    storage = world.place_building("storage", 10, 10, village_id=1, village_uid="v-000001")
    house = world.place_building("house", 14, 10, village_id=1, village_uid="v-000001")
    assert storage is not None and house is not None

    road_system.update_road_infrastructure(world)
    progression = world.compute_progression_snapshot()
    assert int(progression["road_built_with_purpose_count"]) >= 1


def test_settlement_bottleneck_diagnostics_capture_blocked_cluster_and_camp_transition_failure() -> None:
    world = _flat_world()
    world.structures = {(10, 10)}
    world.camps = {
        "camp-000001": {
            "camp_id": "camp-000001",
            "x": 11,
            "y": 10,
            "active": True,
            "village_uid": "",
        }
    }

    world.detect_villages()
    diag = world.compute_settlement_bottleneck_snapshot()
    assert int(diag["village_creation_attempts"]) >= 1
    assert int(diag["village_creation_blocked_count"]) >= 1
    assert int(diag["village_creation_blocked_reasons"].get("insufficient_houses", 0)) >= 1
    assert int(diag["camp_to_village_transition_attempts"]) >= 1
    assert int(diag["camp_to_village_transition_failures"]) >= 1


def test_observability_includes_situated_and_settlement_bottleneck_fields() -> None:
    world = _flat_world()
    world.record_situated_construction_event("construction_on_site_work_ticks")
    world.record_road_purpose_decision(village_uid="v-000001", built=False, reason="no_local_activity")
    world.record_settlement_bottleneck("village_creation_attempts")
    world.record_settlement_bottleneck("village_creation_blocked_count")
    world.record_settlement_bottleneck("village_creation_blocked_reasons", reason="insufficient_houses")
    world.metrics_collector.collect(world)
    snap = world.metrics_collector.latest()
    cog = snap.get("cognition_society", {})
    assert "construction_situated_diagnostics" in cog
    assert "settlement_bottleneck_diagnostics" in cog
    assert "road_built_with_purpose_count" in cog
    assert "road_build_suppressed_no_purpose" in cog
    diag = cog["settlement_bottleneck_diagnostics"]
    assert "secondary_nucleus_structure_count" in diag
    assert "secondary_nucleus_materialization_ticks" in diag


def test_distant_cluster_pull_is_suppressed_when_nearby_viable_camp_exists() -> None:
    world = _flat_world()
    world.camps = {
        "camp-near": {
            "camp_id": "camp-near",
            "x": 9,
            "y": 8,
            "active": True,
            "village_uid": "",
            "support_score": 4,
            "support_nearby_agents": 3,
        },
        "camp-far": {
            "camp_id": "camp-far",
            "x": 20,
            "y": 8,
            "active": True,
            "village_uid": "v-dominant",
            "support_score": 5,
            "support_nearby_agents": 10,
        },
    }
    agent = Agent(x=8, y=8, brain=FoodBrain(), is_player=False, player_id=None)
    agent.village_affiliation_status = "attached"
    agent.primary_village_uid = "v-dominant"
    world.agents = [agent]

    chosen = world.nearest_active_camp_for_agent(agent, max_distance=20)
    assert isinstance(chosen, dict)
    assert str(chosen.get("camp_id", "")) == "camp-near"
    diag = world.compute_settlement_bottleneck_snapshot()
    assert int(diag["distant_cluster_pull_suppressed_count"]) >= 1
    assert int(diag["dominant_cluster_saturation_penalty_applied"]) >= 1


def test_mature_nucleus_can_transition_with_two_houses_when_local_support_is_strong() -> None:
    world = _flat_world()
    world.structures = {(10, 10), (11, 10)}
    world.camps = {
        "camp-000001": {
            "camp_id": "camp-000001",
            "x": 10,
            "y": 11,
            "active": True,
            "support_score": 5,
            "support_nearby_agents": 4,
            "village_uid": "",
        }
    }
    agents = []
    for x in (9, 10, 11):
        a = Agent(x=x, y=10, brain=FoodBrain(), is_player=False, player_id=None)
        a.hunger = 70.0
        agents.append(a)
    world.agents = agents

    world.detect_villages()
    assert len(world.villages) >= 1
    diag = world.compute_settlement_bottleneck_snapshot()
    assert int(diag["mature_nucleus_detected_count"]) >= 1
    assert int(diag["mature_nucleus_successful_transition_count"]) >= 1


def test_immature_two_house_cluster_does_not_transition_to_village() -> None:
    world = _flat_world()
    world.structures = {(10, 10), (11, 10)}
    world.camps = {
        "camp-000001": {
            "camp_id": "camp-000001",
            "x": 10,
            "y": 11,
            "active": True,
            "support_score": 1,
            "support_nearby_agents": 1,
            "village_uid": "",
        }
    }
    agents = []
    for x in (9, 10):
        a = Agent(x=x, y=10, brain=FoodBrain(), is_player=False, player_id=None)
        a.hunger = 65.0
        agents.append(a)
    world.agents = agents

    world.detect_villages()
    assert len(world.villages) == 0
    diag = world.compute_settlement_bottleneck_snapshot()
    assert int(diag["village_creation_blocked_count"]) >= 1


def test_cluster_inertia_is_weak_and_survival_sensitive() -> None:
    world = _flat_world()
    world.camps = {
        "camp-local": {
            "camp_id": "camp-local",
            "x": 9,
            "y": 8,
            "active": True,
            "support_score": 3,
            "support_nearby_agents": 2,
            "ecological_productivity_score": 3.0,
            "village_uid": "",
        },
        "camp-anchored": {
            "camp_id": "camp-anchored",
            "x": 11,
            "y": 8,
            "active": True,
            "support_score": 4,
            "support_nearby_agents": 2,
            "ecological_productivity_score": 3.2,
            "village_uid": "",
        },
    }
    agent = Agent(x=8, y=8, brain=FoodBrain(), is_player=False, player_id=None)
    agent.proto_task_anchor = {"camp_id": "camp-anchored"}
    agent.hunger = 75.0
    world.agents = [agent]
    chosen = world.nearest_active_camp_for_agent(agent, max_distance=10)
    assert isinstance(chosen, dict)
    assert str(chosen.get("camp_id", "")) == "camp-anchored"
    diag = world.compute_settlement_bottleneck_snapshot()
    assert int(diag["cluster_inertia_events"]) >= 1

    agent.hunger = 20.0
    chosen_critical = world.nearest_active_camp_for_agent(agent, max_distance=10)
    assert isinstance(chosen_critical, dict)
    assert str(chosen_critical.get("camp_id", "")) == "camp-local"


def test_ecological_patch_activity_reinforcement_is_bounded() -> None:
    world = _flat_world()
    world.food_rich_patches = [{"center_x": 10, "center_y": 10, "radius": 6}]
    for _ in range(200):
        world.record_food_patch_activity(10, 10, amount=2.5)
    score = world._patch_activity_score_at(10, 10)  # type: ignore[attr-defined]
    assert float(score) <= 120.0
    world._decay_food_patch_activity()  # type: ignore[attr-defined]
    decayed = world._patch_activity_score_at(10, 10)  # type: ignore[attr-defined]
    assert float(decayed) < float(score)


def test_camp_absorption_delay_triggers_then_expires() -> None:
    world = _flat_world()
    world.food = {(10, 10), (11, 10), (10, 11)}
    world.camps = {
        "camp-existing": {
            "camp_id": "camp-existing",
            "x": 13,
            "y": 10,
            "active": True,
            "community_id": "pc-existing",
            "support_nearby_agents": 2,
            "village_uid": "",
            "last_active_tick": 1,
            "created_tick": 1,
            "absence_ticks": 0,
            "food_cache": 0,
        }
    }
    a1 = Agent(x=10, y=10, brain=FoodBrain(), is_player=False, player_id=None)
    a2 = Agent(x=11, y=10, brain=FoodBrain(), is_player=False, player_id=None)
    a1.hunger = 70.0
    a2.hunger = 70.0
    world.agents = [a1, a2]

    for tick in range(1, 4):
        world.tick = tick
        world.update_proto_communities_and_camps()
    diag = world.compute_settlement_bottleneck_snapshot()
    assert int(diag["camp_absorption_delay_events"]) >= 1
    assert len(world.camps) >= 2

    # Force mature streak path where delay no longer applies and absorption can happen.
    world.proto_communities = {
        "pc-force": {
            "community_id": "pc-force",
            "x": 10,
            "y": 10,
            "agent_ids": [a1.agent_id, a2.agent_id],
            "agent_count": 2,
            "streak": 7,
            "last_seen_tick": world.tick,
            "active": True,
        }
    }
    world.tick += 1
    world.update_proto_communities_and_camps()
    diag2 = world.compute_settlement_bottleneck_snapshot()
    assert int(diag2["camp_absorption_events"]) >= 1


def test_low_density_exploration_shift_is_viability_gated() -> None:
    world = _flat_world()
    world.food_rich_patches = [{"center_x": 12, "center_y": 10, "radius": 5}]
    world.food = {(11, 10), (12, 10)}
    agent = Agent(x=10, y=10, brain=FoodBrain(), is_player=False, player_id=None)
    agent.hunger = 70.0
    world.agents = [agent]
    step = world.suggest_low_density_exploration_step(agent)
    assert isinstance(step, tuple) and len(step) == 2
    diag = world.compute_settlement_bottleneck_snapshot()
    assert int(diag["exploration_shift_due_to_low_density"]) >= 1

    agent.hunger = 20.0
    step_critical = world.suggest_low_density_exploration_step(agent)
    assert step_critical is None


def test_secondary_nucleus_build_gravitation_requires_viability() -> None:
    world = _flat_world()
    world.food = {(10, 10), (11, 10)}
    world.camps = {
        "camp-1": {
            "camp_id": "camp-1",
            "x": 10,
            "y": 10,
            "active": True,
            "support_nearby_agents": 3,
            "ecological_productivity_score": 3.0,
        }
    }
    agent = Agent(x=9, y=10, brain=FoodBrain(), is_player=False, player_id=None)
    agent.hunger = 70.0
    world.agents = [agent]

    near_bonus = world.secondary_nucleus_build_position_bonus(agent, (10, 10), "house")
    far_bonus = world.secondary_nucleus_build_position_bonus(agent, (20, 20), "house")
    assert int(near_bonus) > int(far_bonus)

    world.camps["camp-1"]["support_nearby_agents"] = 1
    world.food = set()
    no_viability_bonus = world.secondary_nucleus_build_position_bonus(agent, (10, 10), "house")
    assert int(no_viability_bonus) == 0


def test_builder_continuity_bonus_respects_survival_pressure() -> None:
    world = _flat_world()
    world.camps = {
        "camp-1": {
            "camp_id": "camp-1",
            "x": 10,
            "y": 10,
            "active": True,
            "support_nearby_agents": 3,
            "ecological_productivity_score": 3.0,
        }
    }
    building_system.place_building(
        world,
        "house",
        (11, 10),
        village_id=None,
        village_uid="",
        operational_state="under_construction",
    )
    agent = Agent(x=9, y=10, brain=FoodBrain(), is_player=False, player_id=None)
    world.agents = [agent]

    agent.hunger = 70.0
    assert int(world.secondary_nucleus_builder_continuity_bonus(agent, "build_house")) > 0
    agent.hunger = 20.0
    assert int(world.secondary_nucleus_builder_continuity_bonus(agent, "build_house")) == 0


def test_local_material_delivery_priority_only_when_local_construction_exists() -> None:
    world = _flat_world()
    world.camps = {
        "camp-1": {
            "camp_id": "camp-1",
            "x": 10,
            "y": 10,
            "active": True,
            "support_nearby_agents": 3,
            "ecological_productivity_score": 3.0,
        }
    }
    agent = Agent(x=9, y=10, brain=FoodBrain(), is_player=False, player_id=None)
    agent.hunger = 70.0
    world.agents = [agent]
    site = {"x": 11, "y": 10}
    assert int(world.secondary_nucleus_delivery_priority(agent, site)) == 0

    building_system.place_building(
        world,
        "storage",
        (11, 10),
        village_id=None,
        village_uid="",
        operational_state="under_construction",
    )
    assert int(world.secondary_nucleus_delivery_priority(agent, site)) > 0


def test_secondary_nucleus_structure_cohesion_bonus_is_bounded() -> None:
    world = _flat_world()
    world.camps = {
        "camp-1": {
            "camp_id": "camp-1",
            "x": 10,
            "y": 10,
            "active": True,
            "support_nearby_agents": 4,
            "ecological_productivity_score": 3.5,
        }
    }
    agent = Agent(x=10, y=10, brain=FoodBrain(), is_player=False, player_id=None)
    agent.hunger = 70.0
    world.agents = [agent]
    for x in range(8, 13):
        for y in range(8, 13):
            if (x + y) % 2 == 0:
                world.place_building("house", x, y, village_id=None, village_uid="")
    bonus = int(world.secondary_nucleus_build_position_bonus(agent, (10, 10), "house"))
    assert bonus <= 24


def test_absorption_during_build_is_recorded() -> None:
    world = _flat_world()
    world.food = {(10, 10), (11, 10), (10, 11)}
    world.camps = {
        "camp-existing": {
            "camp_id": "camp-existing",
            "x": 12,
            "y": 10,
            "active": True,
            "community_id": "pc-existing",
            "support_nearby_agents": 2,
            "village_uid": "",
            "last_active_tick": 1,
            "created_tick": 1,
            "absence_ticks": 0,
            "food_cache": 0,
        }
    }
    building_system.place_building(
        world,
        "house",
        (10, 10),
        village_id=None,
        village_uid="",
        operational_state="under_construction",
    )
    a1 = Agent(x=10, y=10, brain=FoodBrain(), is_player=False, player_id=None)
    a2 = Agent(x=11, y=10, brain=FoodBrain(), is_player=False, player_id=None)
    a1.hunger = 70.0
    a2.hunger = 70.0
    world.agents = [a1, a2]

    world.tick = 1
    world.update_proto_communities_and_camps()
    world.proto_communities = {
        "pc-force": {
            "community_id": "pc-force",
            "x": 10,
            "y": 10,
            "agent_ids": [a1.agent_id, a2.agent_id],
            "agent_count": 2,
            "streak": 7,
            "last_seen_tick": world.tick,
            "active": True,
        }
    }
    world.tick = 2
    world.update_proto_communities_and_camps()
    diag = world.compute_settlement_bottleneck_snapshot()
    assert int(diag["secondary_nucleus_absorption_during_build"]) >= 1
