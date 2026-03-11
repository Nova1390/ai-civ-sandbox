from __future__ import annotations

from agent import Agent, LOCAL_LOOP_COMMITMENT_TICKS, evaluate_agent_salience, update_agent_social_memory
from brain import FoodBrain
from world import World


def _flat_world() -> World:
    world = World(width=32, height=32, num_agents=0, seed=42, llm_enabled=False)
    world.tiles = [["G" for _ in range(world.width)] for _ in range(world.height)]
    world.agents = []
    world.villages = []
    world.buildings = {}
    world.structures = set()
    world.storage_buildings = set()
    world.food = set()
    world.wood = set()
    world.stone = set()
    world.roads = set()
    world.transport_tiles = {}
    return world


def _near_entry(agent: Agent, other: Agent) -> dict:
    return {
        "agent_id": other.agent_id,
        "x": other.x,
        "y": other.y,
        "distance": abs(other.x - agent.x) + abs(other.y - agent.y),
        "role": other.role,
        "social_influence": 0.1,
        "same_village": False,
    }


def test_encounter_memory_created_and_familiarity_grows() -> None:
    world = _flat_world()
    a = Agent(x=10, y=10, brain=FoodBrain())
    b = Agent(x=11, y=10, brain=FoodBrain())
    world.agents = [a, b]
    for tick in range(1, 5):
        world.tick = tick
        update_agent_social_memory(world, a, {"nearby_agents": [_near_entry(a, b)]})
    memory = getattr(a, "recent_encounters", {})
    assert b.agent_id in memory
    entry = memory[b.agent_id]
    assert int(entry.get("encounter_count", 0)) >= 4
    assert float(entry.get("familiarity_score", 0.0)) > 0.2


def test_familiarity_decays_when_no_longer_seen() -> None:
    world = _flat_world()
    a = Agent(x=10, y=10, brain=FoodBrain())
    b = Agent(x=11, y=10, brain=FoodBrain())
    world.agents = [a, b]
    world.tick = 1
    update_agent_social_memory(world, a, {"nearby_agents": [_near_entry(a, b)]})
    first = float(a.recent_encounters[b.agent_id]["familiarity_score"])
    world.tick = 30
    update_agent_social_memory(world, a, {"nearby_agents": []})
    second = float(a.recent_encounters[b.agent_id]["familiarity_score"])
    assert second < first


def test_encounter_memory_is_bounded() -> None:
    world = _flat_world()
    a = Agent(x=10, y=10, brain=FoodBrain())
    others = [Agent(x=11 + (i % 3), y=10 + (i // 3), brain=FoodBrain()) for i in range(40)]
    world.agents = [a] + others
    world.tick = 1
    nearby = [_near_entry(a, other) for other in others]
    update_agent_social_memory(world, a, {"nearby_agents": nearby})
    assert len(a.recent_encounters) <= 32


def test_familiarity_weakly_boosts_social_salience() -> None:
    world = _flat_world()
    a = Agent(x=10, y=10, brain=FoodBrain())
    b = Agent(x=11, y=10, brain=FoodBrain())
    world.agents = [a, b]
    base_state = {
        "own_state": {"role": a.role, "task": "idle", "hunger": a.hunger, "assigned_building_id": None},
        "local_signals": {"needs": {}, "market_state": {}, "construction_needs": {}, "priority": "stabilize"},
        "local_culture": {},
        "nearby_resources": {"food": [], "wood": [], "stone": []},
        "nearby_buildings": [],
        "nearby_agents": [_near_entry(a, b)],
    }
    a.subjective_state = dict(base_state)
    no_fam_salience = evaluate_agent_salience(world, a)["top_social_targets"][0]["salience"]
    a.recent_encounters = {
        b.agent_id: {"encounter_count": 8, "last_encounter_tick": 1, "familiarity_score": 0.8}
    }
    a.subjective_state = dict(base_state)
    fam_salience = evaluate_agent_salience(world, a)["top_social_targets"][0]["salience"]
    assert fam_salience > no_fam_salience


def test_social_encounter_metrics_exported_in_snapshot() -> None:
    world = _flat_world()
    a = Agent(x=10, y=10, brain=FoodBrain())
    b = Agent(x=11, y=10, brain=FoodBrain())
    world.agents = [a, b]
    world.tick = 1
    update_agent_social_memory(world, a, {"nearby_agents": [_near_entry(a, b)]})
    world.metrics_collector.collect(world)
    snap = world.metrics_collector.latest()
    social = snap.get("cognition_society", {}).get("social_encounter_global", {})
    assert "total_encounter_events" in social
    assert "familiarity_relationships_count" in social
    assert "avg_familiarity_score" in social


def test_familiar_zone_reinforcement_and_decay_metrics() -> None:
    world = _flat_world()
    a = Agent(x=10, y=10, brain=FoodBrain())
    b = Agent(x=11, y=10, brain=FoodBrain())
    world.agents = [a, b]
    # Prime familiarity.
    for t in range(1, 4):
        world.tick = t
        update_agent_social_memory(world, a, {"nearby_agents": [_near_entry(a, b)]})
    # Inject nearby useful success, then update to reinforce zone.
    a.episodic_memory = {
        "recent_events": [
            {"type": "found_resource", "tick": world.tick, "outcome": "success", "salience": 1.0}
        ]
    }
    world.tick += 1
    update_agent_social_memory(world, a, {"nearby_agents": [_near_entry(a, b)]})
    zones = getattr(a, "recent_familiar_activity_zones", [])
    assert isinstance(zones, list) and len(zones) >= 1
    # Force a stale jump to exercise decay/removal.
    world.tick += 250
    update_agent_social_memory(world, a, {"nearby_agents": []})
    social = world.compute_social_encounter_snapshot()
    assert int(social.get("familiar_zone_reinforcement_events", 0)) >= 1
    assert int(social.get("familiar_zone_score_updates", 0)) >= 1


def test_familiar_zone_score_is_capped_and_density_reinforcement_is_attenuated() -> None:
    world = _flat_world()
    a = Agent(x=10, y=10, brain=FoodBrain())
    b = Agent(x=11, y=10, brain=FoodBrain())
    crowded = [Agent(x=10 + (i % 4), y=9 + (i // 4), brain=FoodBrain()) for i in range(10)]
    world.agents = [a, b] + crowded
    for t in range(1, 6):
        world.tick = t
        nearby = [_near_entry(a, b)] + [_near_entry(a, c) for c in crowded]
        a.episodic_memory = {
            "recent_events": [
                {"type": "found_resource", "tick": world.tick, "outcome": "success", "salience": 1.0}
            ]
        }
        update_agent_social_memory(world, a, {"nearby_agents": nearby})
    zones = getattr(a, "recent_familiar_activity_zones", [])
    assert zones and float(zones[0].get("score", 0.0)) <= 0.78
    social = world.compute_social_encounter_snapshot()
    assert int(social.get("dense_area_social_bias_reductions", 0)) >= 1
    assert int(social.get("familiar_zone_saturation_clamps", 0)) >= 0


def test_loop_continuity_bonus_reduced_in_high_density_but_active_in_low_density() -> None:
    world = _flat_world()
    world.tick = 10
    low = Agent(x=8, y=8, brain=FoodBrain())
    low.proto_specialization = "food_hauler"
    low.inventory["food"] = 1
    low.hunger = 70.0
    low.proto_task_anchor = {"drop_pos": [8, 8], "source_pos": [9, 8]}
    low.subjective_state = {"social_density": {"familiar_nearby_agents_count": 1, "nearby_agents_count": 3}}
    world.update_agent_proto_specialization = lambda _a: None  # type: ignore[assignment]
    low.update_role_task(world)
    low_commit = int(low.camp_loop_commit_until_tick)
    assert low_commit == world.tick + int(LOCAL_LOOP_COMMITMENT_TICKS) + 2

    high = Agent(x=8, y=8, brain=FoodBrain())
    high.proto_specialization = "food_hauler"
    high.inventory["food"] = 1
    high.hunger = 70.0
    high.proto_task_anchor = {"drop_pos": [8, 8], "source_pos": [9, 8]}
    high.subjective_state = {"social_density": {"familiar_nearby_agents_count": 2, "nearby_agents_count": 10}}
    high.update_role_task(world)
    high_commit = int(high.camp_loop_commit_until_tick)
    assert high_commit == world.tick + int(LOCAL_LOOP_COMMITMENT_TICKS) + 1
    social = world.compute_social_encounter_snapshot()
    assert int(social.get("familiar_loop_continuity_bonus", 0)) >= 2
    assert int(social.get("density_safe_loop_bonus_reduced_count", 0)) >= 1


def test_familiar_zone_salience_bonus_attenuates_under_high_density_not_to_zero() -> None:
    world = _flat_world()
    a = Agent(x=10, y=10, brain=FoodBrain())
    food_entry = {"x": 11, "y": 10, "distance": 1}
    zone = {"x": 11, "y": 10, "score": 0.75, "last_tick": 1, "use_count": 2}
    low_state = {
        "own_state": {"role": "npc", "task": "idle", "hunger": 75.0, "assigned_building_id": None},
        "local_signals": {"needs": {}, "market_state": {}, "construction_needs": {}, "priority": "stabilize"},
        "local_culture": {},
        "nearby_resources": {"food": [food_entry], "wood": [], "stone": []},
        "nearby_buildings": [],
        "nearby_agents": [{"agent_id": "x", "x": 12, "y": 10, "distance": 2, "role": "npc", "same_village": False, "social_influence": 0.0}],
    }
    high_agents = [
        {"agent_id": f"a{i}", "x": 12 + (i % 3), "y": 10 + (i // 3), "distance": 2 + (i % 2), "role": "npc", "same_village": False, "social_influence": 0.0}
        for i in range(10)
    ]
    high_state = dict(low_state)
    high_state["nearby_agents"] = high_agents

    a.recent_familiar_activity_zones = [dict(zone)]
    a.subjective_state = low_state
    low_salience = float(evaluate_agent_salience(world, a)["top_resource_targets"][0]["salience"])
    a.recent_familiar_activity_zones = [dict(zone)]
    a.subjective_state = high_state
    high_salience = float(evaluate_agent_salience(world, a)["top_resource_targets"][0]["salience"])
    assert low_salience > high_salience
    assert high_salience > 0.0
