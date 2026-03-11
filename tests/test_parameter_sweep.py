from __future__ import annotations

from systems.global_balance_runner import GlobalBalanceScenarioConfig, GlobalBalanceThresholds, run_global_balance_scenario
from systems.parameter_sweep import (
    aggregate_across_families,
    generate_sweep_configs,
    is_breakeven_candidate,
)
import agent as agent_module
import world as world_module


def test_generate_sweep_configs_is_deterministic_and_capped() -> None:
    ranges = {
        "food_regeneration_rate": (0.8, 1.0, 1.2),
        "hunger_decay_rate": (0.9, 1.0, 1.1),
        "camp_food_buffer_capacity": (0.75, 1.0, 1.25),
    }
    a = generate_sweep_configs(ranges=ranges, max_configs=4, deterministic_seed=42)
    b = generate_sweep_configs(ranges=ranges, max_configs=4, deterministic_seed=42)
    c = generate_sweep_configs(ranges=ranges, max_configs=4, deterministic_seed=43)
    assert len(a) == 4
    assert [x.config_id for x in a] == [x.config_id for x in b]
    assert [x.config_id for x in a] != [x.config_id for x in c]


def test_parameter_overrides_apply_and_restore() -> None:
    base_hunger_decay = float(agent_module.BASE_HUNGER_DECAY_PER_TICK)
    base_camp_cap = int(world_module.CAMP_FOOD_CACHE_CAPACITY)
    cfg = GlobalBalanceScenarioConfig(
        name="override_probe",
        seed=777,
        width=24,
        height=24,
        initial_population=12,
        ticks=8,
        snapshot_interval=2,
        history_limit=20,
        llm_enabled=False,
        parameter_overrides={
            "hunger_decay_rate": 1.1,
            "camp_food_buffer_capacity": 1.5,
            "eat_trigger_threshold": 54.0,
        },
    )
    payload = run_global_balance_scenario(cfg, thresholds=GlobalBalanceThresholds())
    assert isinstance(payload, dict)
    assert float(agent_module.BASE_HUNGER_DECAY_PER_TICK) == base_hunger_decay
    assert int(world_module.CAMP_FOOD_CACHE_CAPACITY) == base_camp_cap


def test_aggregate_across_families_is_deterministic() -> None:
    fam = {
        "baseline": {"avg_final_population": 10.0, "extinction_run_ratio": 0.0},
        "food_stress": {"avg_final_population": 6.0, "extinction_run_ratio": 0.2},
    }
    agg = aggregate_across_families(fam)
    assert float(agg["avg_final_population"]) == 8.0
    assert float(agg["extinction_run_ratio"]) == 0.1


def test_breakeven_detection_logic() -> None:
    baseline = {
        "avg_final_population": 10.0,
        "avg_repeated_successful_loop_count": 20.0,
    }
    improved = {
        "extinction_run_ratio": 0.0,
        "avg_repeated_successful_loop_count": 24.0,
        "avg_active_cultural_practices": 1.0,
        "avg_final_population": 11.0,
    }
    non_candidate = {
        "extinction_run_ratio": 0.2,
        "avg_repeated_successful_loop_count": 30.0,
        "avg_active_cultural_practices": 2.0,
        "avg_final_population": 12.0,
    }
    assert is_breakeven_candidate(aggregate_all=improved, baseline_reference=baseline) is True
    assert is_breakeven_candidate(aggregate_all=non_candidate, baseline_reference=baseline) is False
