from __future__ import annotations

from scripts.run_behavior_map_validation import aggregate_behavior_runs
from world import World


def test_behavior_activity_and_transition_counters_increment() -> None:
    world = World(width=24, height=24, num_agents=0, seed=7, llm_enabled=False)
    world.record_behavior_activity("gather_food", x=5, y=5, count=2)
    world.record_behavior_activity("camp_supply_food", x=5, y=6, count=1)
    world.record_behavior_transition("wander", "gather_food", x=5, y=5)
    world.record_behavior_transition("gather_food", "camp_supply_food", x=5, y=6, count=3)

    snap = world.compute_behavior_map_snapshot()
    assert int(snap["activity_counts"]["gather_food"]) == 2
    assert int(snap["activity_counts"]["camp_supply_food"]) == 1
    assert int(snap["task_transition_counts"]["wander->gather_food"]) == 1
    assert int(snap["task_transition_counts"]["gather_food->camp_supply_food"]) == 3
    assert isinstance(snap.get("top_task_transitions"), list)
    assert isinstance(snap.get("activity_heatmap_by_type"), dict)


def test_secondary_nucleus_lifecycle_counters_increment() -> None:
    world = World(width=24, height=24, num_agents=0, seed=8, llm_enabled=False)
    world.record_secondary_nucleus_event("secondary_nucleus_birth_count", count=2)
    world.record_secondary_nucleus_event("secondary_nucleus_persistence_ticks", count=11)
    world.record_secondary_nucleus_event("secondary_nucleus_absorption_count", count=1)
    world.record_secondary_nucleus_event("secondary_nucleus_village_attempts", count=3)

    snap = world.compute_behavior_map_snapshot()
    lifecycle = snap["secondary_nucleus_lifecycle"]
    assert int(lifecycle["secondary_nucleus_birth_count"]) == 2
    assert int(lifecycle["secondary_nucleus_persistence_ticks"]) == 11
    assert int(lifecycle["secondary_nucleus_absorption_count"]) == 1
    assert int(lifecycle["secondary_nucleus_village_attempts"]) == 3


def test_behavior_aggregate_schema_contains_expected_fields() -> None:
    run_payload = {
        "metrics": {
            "behavior_map": {
                "activity_counts": {"gather_food": 4},
                "task_transition_counts": {"wander->gather_food": 2},
                "activity_context_counts": {"gather_food:near_food_patch": 3},
                "activity_heatmap_by_type": {"gather_food": {"1:1": 4}},
                "task_transition_by_region": {"1:1": {"wander->gather_food": 2}},
                "secondary_nucleus_lifecycle": {
                    "secondary_nucleus_birth_count": 1,
                    "secondary_nucleus_persistence_ticks": 6,
                    "secondary_nucleus_absorption_count": 0,
                    "secondary_nucleus_decay_count": 1,
                    "secondary_nucleus_village_attempts": 1,
                    "secondary_nucleus_village_successes": 0,
                },
                "cluster_population_distribution_summary": {
                    "active_cluster_count": 2,
                    "top_cluster_population": 8,
                    "secondary_cluster_nonzero_count": 1,
                    "secondary_cluster_avg_population": 3.0,
                },
            }
        }
    }
    agg = aggregate_behavior_runs(scenario_family="baseline", runs=[run_payload, run_payload])
    assert int(agg["run_count"]) == 2
    assert "activity_counts" in agg
    assert "task_transition_counts" in agg
    assert "top_task_transitions" in agg
    assert "secondary_nucleus_lifecycle" in agg
    assert int(agg["secondary_nucleus_lifecycle"]["secondary_nucleus_birth_count"]) == 2
