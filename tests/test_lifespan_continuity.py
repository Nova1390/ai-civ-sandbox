from __future__ import annotations

from agent import (
    Agent,
    KNOWLEDGE_MIN_CONFIDENCE,
    ROUTINE_SUCCESS_EXTENSION_TICKS,
    decay_agent_knowledge_state,
    ensure_agent_knowledge_state,
    update_agent_knowledge_from_experience,
    write_episodic_memory_event,
)
from world import World


def _flat_world() -> World:
    world = World(width=24, height=24, num_agents=0, seed=42, llm_enabled=False)
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


def test_repeated_confirmations_reduce_decay_and_increase_memory_age_signal() -> None:
    world = _flat_world()
    agent = Agent(x=10, y=10, brain=None)
    state = ensure_agent_knowledge_state(agent)
    state["known_resource_spots"] = [
        {
            "type": "resource_spot",
            "subject": "food",
            "location": {"x": 11, "y": 10},
            "learned_tick": 0,
            "last_confirmed_tick": 100,
            "confirmations": 5,
            "confidence": 0.70,
            "source": "direct",
            "salience": 0.9,
        },
        {
            "type": "resource_spot",
            "subject": "wood",
            "location": {"x": 12, "y": 10},
            "learned_tick": 0,
            "last_confirmed_tick": 0,
            "confirmations": 1,
            "confidence": 0.70,
            "source": "social",
            "salience": 0.5,
        },
    ]
    world.tick = 100
    decay_agent_knowledge_state(world, agent)
    reinforced = next(e for e in state["known_resource_spots"] if str(e.get("subject", "")) == "food")
    weak = next(e for e in state["known_resource_spots"] if str(e.get("subject", "")) == "wood")
    assert float(reinforced.get("confidence", 0.0)) > float(weak.get("confidence", 0.0))
    comm = world.compute_communication_snapshot()
    assert int(comm.get("confirmed_memory_reinforcements", 0)) >= 1


def test_direct_memory_invalidation_recorded_when_failed_search_contradicts_memory() -> None:
    world = _flat_world()
    agent = Agent(x=10, y=10, brain=None)
    state = ensure_agent_knowledge_state(agent)
    state["known_resource_spots"] = [
        {
            "type": "resource_spot",
            "subject": "food",
            "location": {"x": 11, "y": 10},
            "learned_tick": 1,
            "confidence": 0.2,
            "source": "direct",
            "salience": 0.6,
        }
    ]
    world.tick = 10
    write_episodic_memory_event(
        agent,
        tick=world.tick,
        event_type="failed_resource_search",
        outcome="failure",
        location=(11, 10),
        resource_type="food",
        salience=0.8,
    )
    update_agent_knowledge_from_experience(world, agent)
    assert float(state["known_resource_spots"][0]["confidence"]) < float(KNOWLEDGE_MIN_CONFIDENCE)
    comm = world.compute_communication_snapshot()
    assert int(comm.get("direct_memory_invalidations", 0)) >= 1


def test_successful_routine_retention_extends_persistence_window() -> None:
    world = _flat_world()
    agent = Agent(x=8, y=8, brain=None)
    world.agents = [agent]
    agent.role = "farmer"
    agent.village_id = 1
    agent.task = "farm_cycle"
    agent.role_task_persisted_task = "farm_cycle"
    world.tick = 20
    agent.role_task_persistence_until_tick = int(world.tick) + 1
    agent.hunger = 80.0
    agent.sleep_need = 5.0
    agent.fatigue = 5.0
    world.villages = [
        {
            "id": 1,
            "village_uid": "v-000001",
            "priority": "stabilize",
            "needs": {},
            "storage": {},
            "population": 3,
            "center": {"x": 8, "y": 8},
        }
    ]
    world.is_farmer_task_viable = lambda _a: True  # type: ignore[assignment]
    write_episodic_memory_event(
        agent,
        tick=world.tick,
        event_type="farm_work",
        outcome="success",
        location=(8, 8),
        salience=0.9,
    )
    agent.update_role_task(world)
    assert str(agent.task) == "farm_cycle"
    assert int(agent.role_task_persistence_until_tick) >= int(world.tick) + int(ROUTINE_SUCCESS_EXTENSION_TICKS)
    metrics = world.compute_settlement_progression_snapshot()
    assert int(metrics.get("routine_persistence_ticks", 0)) >= 1
    assert int(metrics.get("repeated_successful_loop_count", 0)) >= 1
