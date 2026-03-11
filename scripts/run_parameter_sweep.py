from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from systems.global_balance_runner import (
    GlobalBalanceScenarioConfig,
    GlobalBalanceThresholds,
    aggregate_global_balance_results,
    run_global_balance_scenario,
)
from systems.parameter_sweep import (
    DEFAULT_SWEEP_RANGES,
    aggregate_across_families,
    build_influence_ranking,
    generate_sweep_configs,
    is_breakeven_candidate,
    score_configuration,
    summarize_family_aggregate,
)


def _family_configs(
    *,
    family_name: str,
    seeds: List[int],
    ticks: int,
    snapshot_interval: int,
    history_limit: int,
    parameter_overrides: Dict[str, float] | None = None,
) -> List[GlobalBalanceScenarioConfig]:
    out: List[GlobalBalanceScenarioConfig] = []
    for seed in seeds:
        if family_name == "baseline":
            out.append(
                GlobalBalanceScenarioConfig(
                    name=f"baseline_seed_{seed}",
                    seed=int(seed),
                    width=72,
                    height=72,
                    initial_population=40,
                    ticks=int(ticks),
                    snapshot_interval=int(snapshot_interval),
                    history_limit=int(history_limit),
                    llm_enabled=False,
                    food_multiplier=1.0,
                    parameter_overrides=dict(parameter_overrides or {}),
                )
            )
        elif family_name == "food_stress":
            out.append(
                GlobalBalanceScenarioConfig(
                    name=f"food_stress_seed_{seed}",
                    seed=int(seed),
                    width=72,
                    height=72,
                    initial_population=45,
                    ticks=int(ticks),
                    snapshot_interval=int(snapshot_interval),
                    history_limit=int(history_limit),
                    llm_enabled=False,
                    food_multiplier=0.65,
                    parameter_overrides=dict(parameter_overrides or {}),
                )
            )
        elif family_name == "population_variant":
            out.append(
                GlobalBalanceScenarioConfig(
                    name=f"population_variant_seed_{seed}",
                    seed=int(seed),
                    width=72,
                    height=72,
                    initial_population=55,
                    ticks=int(ticks),
                    snapshot_interval=int(snapshot_interval),
                    history_limit=int(history_limit),
                    llm_enabled=False,
                    food_multiplier=1.0,
                    parameter_overrides=dict(parameter_overrides or {}),
                )
            )
        elif family_name == "reduced_pressure":
            out.append(
                GlobalBalanceScenarioConfig(
                    name=f"reduced_pressure_seed_{seed}",
                    seed=int(seed),
                    width=72,
                    height=72,
                    initial_population=40,
                    ticks=int(ticks),
                    snapshot_interval=int(snapshot_interval),
                    history_limit=int(history_limit),
                    llm_enabled=False,
                    food_multiplier=1.2,
                    parameter_overrides=dict(parameter_overrides or {}),
                )
            )
        else:
            raise ValueError(f"Unknown scenario family: {family_name}")
    return out


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _build_summary(
    *,
    args: argparse.Namespace,
    thresholds: GlobalBalanceThresholds,
    families: List[str],
    results: List[Dict[str, Any]],
    baseline_reference_metrics: Dict[str, float],
    influence: List[Dict[str, Any]],
    candidates: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "run_configuration": {
            "ticks": int(args.ticks),
            "snapshot_interval": int(args.snapshot_interval),
            "history_limit": int(args.history_limit),
            "seeds": [int(s) for s in args.seeds],
            "families": list(families),
            "max_configs": int(args.max_configs),
            "sweep_seed": int(args.sweep_seed),
            "dry_run": bool(args.dry_run),
        },
        "analysis_thresholds": {
            "min_legit_village_population": int(thresholds.min_legit_village_population),
            "min_legit_leader_village_population": int(thresholds.min_legit_leader_village_population),
            "early_extinction_threshold_tick": int(thresholds.early_extinction_threshold_tick),
            "early_mass_death_threshold_ratio": float(thresholds.early_mass_death_threshold_ratio),
        },
        "baseline_reference_metrics": dict(baseline_reference_metrics),
        "results_count": int(len(results)),
        "breakeven_candidate_count": int(len(candidates)),
        "parameter_influence_ranking": influence,
    }


def _persist_outputs(
    *,
    out_dir: Path,
    args: argparse.Namespace,
    thresholds: GlobalBalanceThresholds,
    families: List[str],
    results: List[Dict[str, Any]],
    baseline_reference_metrics: Dict[str, float],
) -> None:
    ranked = sorted(results, key=lambda r: float(r.get("score", 0.0)), reverse=True)
    candidates = [r for r in ranked if bool(r.get("breakeven_candidate", False))]
    influence = build_influence_ranking(ranked)
    summary = _build_summary(
        args=args,
        thresholds=thresholds,
        families=families,
        results=results,
        baseline_reference_metrics=baseline_reference_metrics,
        influence=influence,
        candidates=candidates,
    )
    _write_json(out_dir / "breakeven_sweep_results.json", {"summary": summary, "configs": results})
    _write_json(out_dir / "breakeven_ranked_configs.json", {"summary": summary, "ranked_configs": ranked})
    _write_json(out_dir / "breakeven_candidate_configs.json", {"summary": summary, "candidate_configs": candidates})


def main() -> None:
    parser = argparse.ArgumentParser(description="Run environment/agent parameter sweep and detect breakeven configurations.")
    parser.add_argument("--out-dir", type=str, default="analysis_outputs/breakeven_sweep")
    parser.add_argument("--ticks", type=int, default=1600)
    parser.add_argument("--snapshot-interval", type=int, default=10)
    parser.add_argument("--history-limit", type=int, default=300)
    parser.add_argument("--seeds", type=int, nargs="+", default=[4242, 5151, 6262, 7373, 8484])
    parser.add_argument("--max-configs", type=int, default=24)
    parser.add_argument("--sweep-seed", type=int, default=1337)
    parser.add_argument("--include-reduced-pressure", action="store_true")
    parser.add_argument("--min-legit-village-population", type=int, default=2)
    parser.add_argument("--min-legit-leader-village-population", type=int, default=3)
    parser.add_argument("--early-extinction-threshold-tick", type=int, default=200)
    parser.add_argument("--early-mass-death-threshold-ratio", type=float, default=0.5)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    thresholds = GlobalBalanceThresholds(
        min_legit_village_population=max(1, int(args.min_legit_village_population)),
        min_legit_leader_village_population=max(1, int(args.min_legit_leader_village_population)),
        early_extinction_threshold_tick=max(1, int(args.early_extinction_threshold_tick)),
        early_mass_death_threshold_ratio=max(0.0, min(1.0, float(args.early_mass_death_threshold_ratio))),
    )

    families = ["baseline", "food_stress", "population_variant"]
    if bool(args.include_reduced_pressure):
        families.append("reduced_pressure")

    sweep_configs = generate_sweep_configs(
        ranges=DEFAULT_SWEEP_RANGES,
        max_configs=max(1, int(args.max_configs)),
        deterministic_seed=int(args.sweep_seed),
    )
    baseline_config = {
        "config_id": "baseline_reference",
        "parameters": {k: 1.0 for k in DEFAULT_SWEEP_RANGES.keys()},
        "is_baseline": True,
    }
    config_payloads = [baseline_config] + [
        {"config_id": c.config_id, "parameters": dict(c.parameters), "is_baseline": False}
        for c in sweep_configs
    ]

    results: List[Dict[str, Any]] = []
    baseline_reference_metrics: Dict[str, float] = {}

    for cfg_entry in config_payloads:
        cfg_id = str(cfg_entry["config_id"])
        params = dict(cfg_entry["parameters"])
        is_baseline = bool(cfg_entry.get("is_baseline", False))
        family_results: Dict[str, Dict[str, Any]] = {}
        family_aggregates: Dict[str, Dict[str, float]] = {}
        for family in families:
            runs: List[Dict[str, Any]] = []
            if not bool(args.dry_run):
                for scfg in _family_configs(
                    family_name=family,
                    seeds=[int(s) for s in args.seeds],
                    ticks=int(args.ticks),
                    snapshot_interval=int(args.snapshot_interval),
                    history_limit=int(args.history_limit),
                    parameter_overrides=params,
                ):
                    runs.append(run_global_balance_scenario(scfg, thresholds=thresholds))
            family_payload = aggregate_global_balance_results(
                scenario_family=family,
                runs=runs,
                thresholds=thresholds,
            )
            family_results[family] = family_payload
            family_aggregates[family] = summarize_family_aggregate(dict(family_payload.get("aggregate", {})))
        aggregate_all = aggregate_across_families(family_aggregates)
        if is_baseline:
            baseline_reference_metrics = dict(aggregate_all)
        breakeven = is_breakeven_candidate(
            aggregate_all=aggregate_all,
            baseline_reference=baseline_reference_metrics or aggregate_all,
        )
        score = score_configuration(aggregate_all)
        results.append(
            {
                "config_id": cfg_id,
                "is_baseline": is_baseline,
                "parameters": params,
                "scenario_family_aggregates": family_aggregates,
                "aggregate_all_families": aggregate_all,
                "breakeven_candidate": bool(breakeven),
                "score": float(round(score, 6)),
            }
        )

        _persist_outputs(
            out_dir=out_dir,
            args=args,
            thresholds=thresholds,
            families=families,
            results=results,
            baseline_reference_metrics=baseline_reference_metrics,
        )

    print("Parameter sweep completed.")
    print(str(out_dir / "breakeven_sweep_results.json"))
    print(str(out_dir / "breakeven_ranked_configs.json"))
    print(str(out_dir / "breakeven_candidate_configs.json"))


if __name__ == "__main__":
    main()
