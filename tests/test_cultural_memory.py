from __future__ import annotations

from agent import Agent, build_agent_perception, evaluate_agent_salience
from brain import FoodBrain
from world import World


def _world() -> World:
    world = World(width=24, height=24, num_agents=0, seed=909, llm_enabled=False)
    world.tiles = [["G" for _ in range(world.width)] for _ in range(world.height)]
    world.food = set()
    world.wood = set()
    world.stone = set()
    world.farms = set()
    world.farm_plots = {}
    world.camps = {}
    world.buildings = {}
    world.structures = set()
    world.storage_buildings = set()
    world.villages = [
        {
            "id": 1,
            "village_uid": "v-000001",
            "center": {"x": 8, "y": 8},
            "farm_zone_center": {"x": 8, "y": 8},
            "population": 6,
            "houses": 2,
            "storage": {"food": 0, "wood": 0, "stone": 0},
            "needs": {"food_low": True},
        }
    ]
    return world


def test_repeated_successful_gather_creates_local_practice_memory() -> None:
    world = _world()
    agent = Agent(x=8, y=8, brain=None, is_player=False, player_id=None)
    agent.village_id = 1
    world.food.add((8, 8))
    for _ in range(3):
        world.tick += 1
        world.food.add((8, 8))
        world.autopickup(agent)
    world.update_settlement_progression_metrics()
    snap = world.compute_settlement_progression_snapshot()
    assert int(snap["cultural_practices_created"]) >= 1
    assert int(snap["productive_food_patch_practices"]) >= 1
    assert any(str(v.get("practice_type", "")) == "productive_food_patch" for v in world.local_practice_memory.values())


def test_cultural_memory_decays_when_unused() -> None:
    world = _world()
    world.record_local_practice("productive_food_patch", x=8, y=8, weight=0.6, decay_rate=0.03)
    for _ in range(120):
        world.tick += 1
        world._decay_local_practice_memory()
    assert len(world.local_practice_memory) == 0
    snap = world.compute_settlement_progression_snapshot()
    assert int(snap["cultural_practices_decayed"]) >= 1


def test_cultural_memory_is_spatially_local() -> None:
    world = _world()
    for _ in range(3):
        world.record_local_practice("proto_farm_area", x=8, y=8, weight=1.0, decay_rate=0.005)
    near = world.get_local_practice_bias(8, 8)
    far = world.get_local_practice_bias(22, 22)
    assert float(near.get("any", 0.0)) > 0.0
    assert float(far.get("any", 0.0)) == 0.0


def test_agents_near_practice_receive_soft_salience_bias() -> None:
    world = _world()
    world.food = {(9, 8)}
    agent = Agent(x=8, y=8, brain=None, is_player=False, player_id=None)
    agent.village_id = 1

    agent.subjective_state = build_agent_perception(world, agent)
    base = evaluate_agent_salience(world, agent)
    base_salience = float(base.get("top_resource_targets", [{}])[0].get("salience", 0.0))

    for _ in range(3):
        world.record_local_practice("productive_food_patch", x=8, y=8, weight=1.0, decay_rate=0.005)
    agent.subjective_state = build_agent_perception(world, agent)
    biased = evaluate_agent_salience(world, agent)
    biased_salience = float(biased.get("top_resource_targets", [{}])[0].get("salience", 0.0))

    assert biased_salience > base_salience
    snap = world.compute_settlement_progression_snapshot()
    assert int(snap["agents_using_cultural_memory_bias"]) >= 1


def test_survival_override_still_wins_over_cultural_bias() -> None:
    world = _world()
    world.food = {(8, 9)}
    for _ in range(4):
        world.record_local_practice("construction_cluster", x=8, y=8, weight=1.0, decay_rate=0.005)
    agent = Agent(x=8, y=8, brain=FoodBrain(), is_player=False, player_id=None)
    agent.village_id = 1
    agent.hunger = 10.0
    agent.task = "build_house"

    action = agent.brain.decide(agent, world)
    assert action[0] == "move"
    assert (agent.x + int(action[1]), agent.y + int(action[2])) == (8, 9)
