from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List

from systems.global_balance_runner import (
    GlobalBalanceScenarioConfig,
    GlobalBalanceThresholds,
    run_global_balance_scenario,
)


def _family_configs(
    *,
    family_name: str,
    seeds: List[int],
    ticks: int,
    snapshot_interval: int,
    history_limit: int,
) -> List[GlobalBalanceScenarioConfig]:
    family_name = str(family_name)
    cfgs: List[GlobalBalanceScenarioConfig] = []
    for seed in seeds:
        if family_name == "baseline":
            cfgs.append(
                GlobalBalanceScenarioConfig(
                    name=f"behavior_baseline_seed_{seed}",
                    seed=int(seed),
                    width=72,
                    height=72,
                    initial_population=40,
                    ticks=int(ticks),
                    snapshot_interval=int(snapshot_interval),
                    history_limit=int(history_limit),
                    llm_enabled=False,
                    food_multiplier=1.0,
                )
            )
        elif family_name == "food_stress":
            cfgs.append(
                GlobalBalanceScenarioConfig(
                    name=f"behavior_food_stress_seed_{seed}",
                    seed=int(seed),
                    width=72,
                    height=72,
                    initial_population=45,
                    ticks=int(ticks),
                    snapshot_interval=int(snapshot_interval),
                    history_limit=int(history_limit),
                    llm_enabled=False,
                    food_multiplier=0.65,
                )
            )
        elif family_name == "population_variant":
            cfgs.append(
                GlobalBalanceScenarioConfig(
                    name=f"behavior_population_variant_seed_{seed}",
                    seed=int(seed),
                    width=72,
                    height=72,
                    initial_population=55,
                    ticks=int(ticks),
                    snapshot_interval=int(snapshot_interval),
                    history_limit=int(history_limit),
                    llm_enabled=False,
                    food_multiplier=1.0,
                )
            )
        elif family_name == "reduced_pressure":
            cfgs.append(
                GlobalBalanceScenarioConfig(
                    name=f"behavior_reduced_pressure_seed_{seed}",
                    seed=int(seed),
                    width=72,
                    height=72,
                    initial_population=40,
                    ticks=int(ticks),
                    snapshot_interval=int(snapshot_interval),
                    history_limit=int(history_limit),
                    llm_enabled=False,
                    food_multiplier=1.2,
                )
            )
        else:
            raise ValueError(f"Unknown scenario family: {family_name}")
    return cfgs


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _sum_nested(dst: Dict[str, int], src: Dict[str, Any]) -> None:
    for key, value in (src.items() if isinstance(src, dict) else []):
        if isinstance(value, (int, float)):
            dst[str(key)] = int(dst.get(str(key), 0)) + int(value)


def _top_n(mapping: Dict[str, int], limit: int = 12) -> List[Dict[str, Any]]:
    ranked = sorted(mapping.items(), key=lambda item: (-int(item[1]), str(item[0])))[: max(1, int(limit))]
    return [{"key": str(k), "count": int(v)} for k, v in ranked]


def aggregate_behavior_runs(*, scenario_family: str, runs: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    run_list = [r for r in runs if isinstance(r, dict)]

    activity_counts: Dict[str, int] = {}
    transition_counts: Dict[str, int] = {}
    activity_context_counts: Dict[str, int] = {}
    activity_by_type_region: Dict[str, Dict[str, int]] = {}
    task_transition_by_region: Dict[str, Dict[str, int]] = {}
    secondary_lifecycle: Dict[str, int] = defaultdict(int)
    cluster_distribution_samples: List[Dict[str, Any]] = []

    for run in run_list:
        behavior: Dict[str, Any] = {}
        if isinstance(run.get("behavior_map"), dict):
            behavior = dict(run.get("behavior_map", {}))
        elif isinstance(run.get("metrics"), dict):
            behavior = dict((run.get("metrics", {}) or {}).get("behavior_map", {}))
        if not isinstance(behavior, dict):
            continue
        _sum_nested(activity_counts, behavior.get("activity_counts", {}))
        _sum_nested(transition_counts, behavior.get("task_transition_counts", {}))
        _sum_nested(activity_context_counts, behavior.get("activity_context_counts", {}))

        for activity_type, region_map in (behavior.get("activity_heatmap_by_type", {}) or {}).items():
            if not isinstance(region_map, dict):
                continue
            dst_region = activity_by_type_region.setdefault(str(activity_type), {})
            _sum_nested(dst_region, region_map)

        for region, transition_map in (behavior.get("task_transition_by_region", {}) or {}).items():
            if not isinstance(transition_map, dict):
                continue
            dst_region = task_transition_by_region.setdefault(str(region), {})
            _sum_nested(dst_region, transition_map)

        for key, value in (behavior.get("secondary_nucleus_lifecycle", {}) or {}).items():
            if isinstance(value, (int, float)):
                secondary_lifecycle[str(key)] += int(value)

        cluster_summary = behavior.get("cluster_population_distribution_summary", {})
        if isinstance(cluster_summary, dict):
            cluster_distribution_samples.append(
                {
                    "active_cluster_count": int(cluster_summary.get("active_cluster_count", 0)),
                    "top_cluster_population": int(cluster_summary.get("top_cluster_population", 0)),
                    "secondary_cluster_nonzero_count": int(cluster_summary.get("secondary_cluster_nonzero_count", 0)),
                    "secondary_cluster_avg_population": float(cluster_summary.get("secondary_cluster_avg_population", 0.0)),
                }
            )

    top_regions_by_type: Dict[str, List[Dict[str, Any]]] = {}
    for activity_type, region_map in activity_by_type_region.items():
        top_regions_by_type[activity_type] = _top_n(region_map, limit=8)

    top_transitions = _top_n(transition_counts, limit=24)
    top_activity = _top_n(activity_counts, limit=24)
    top_activity_context = _top_n(activity_context_counts, limit=24)

    region_transition_totals: Dict[str, int] = {
        region: int(sum(int(v) for v in region_map.values()))
        for region, region_map in task_transition_by_region.items()
    }
    top_transition_regions = _top_n(region_transition_totals, limit=12)

    avg_cluster_summary = {
        "samples": int(len(cluster_distribution_samples)),
        "avg_active_cluster_count": round(
            sum(s["active_cluster_count"] for s in cluster_distribution_samples) / max(1, len(cluster_distribution_samples)),
            3,
        ),
        "avg_top_cluster_population": round(
            sum(s["top_cluster_population"] for s in cluster_distribution_samples) / max(1, len(cluster_distribution_samples)),
            3,
        ),
        "avg_secondary_cluster_nonzero_count": round(
            sum(s["secondary_cluster_nonzero_count"] for s in cluster_distribution_samples) / max(1, len(cluster_distribution_samples)),
            3,
        ),
        "avg_secondary_cluster_population": round(
            sum(s["secondary_cluster_avg_population"] for s in cluster_distribution_samples) / max(1, len(cluster_distribution_samples)),
            3,
        ),
    }

    return {
        "scenario_family": str(scenario_family),
        "run_count": int(len(run_list)),
        "activity_counts": {k: int(v) for k, v in sorted(activity_counts.items(), key=lambda item: item[0])},
        "task_transition_counts": {k: int(v) for k, v in sorted(transition_counts.items(), key=lambda item: item[0])},
        "activity_context_counts": {k: int(v) for k, v in sorted(activity_context_counts.items(), key=lambda item: item[0])},
        "activity_heatmap_by_type": {
            str(k): {rk: int(rv) for rk, rv in sorted(v.items(), key=lambda item: item[0])}
            for k, v in sorted(activity_by_type_region.items(), key=lambda item: item[0])
        },
        "task_transition_by_region": {
            str(k): {tk: int(tv) for tk, tv in sorted(v.items(), key=lambda item: item[0])}
            for k, v in sorted(task_transition_by_region.items(), key=lambda item: item[0])
        },
        "top_active_regions_by_type": top_regions_by_type,
        "top_task_transitions": top_transitions,
        "top_activity_types": top_activity,
        "top_activity_contexts": top_activity_context,
        "top_transition_regions": top_transition_regions,
        "secondary_nucleus_lifecycle": {k: int(v) for k, v in sorted(secondary_lifecycle.items(), key=lambda item: item[0])},
        "cluster_population_distribution_summary_avg": avg_cluster_summary,
        "runs": run_list,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run aggregate spatial behavior and transition mapping scenarios.")
    parser.add_argument("--out-dir", type=str, default="analysis_outputs")
    parser.add_argument("--ticks", type=int, default=1200)
    parser.add_argument("--snapshot-interval", type=int, default=10)
    parser.add_argument("--history-limit", type=int, default=300)
    parser.add_argument("--seeds", type=int, nargs="+", default=[4242, 5151, 6262])
    args = parser.parse_args()

    thresholds = GlobalBalanceThresholds()
    families = ["baseline", "food_stress", "population_variant", "reduced_pressure"]
    artifacts: Dict[str, Dict[str, Any]] = {}
    out_dir = Path(args.out_dir)

    for family in families:
        runs: List[Dict[str, Any]] = []
        for cfg in _family_configs(
            family_name=family,
            seeds=[int(s) for s in args.seeds],
            ticks=int(args.ticks),
            snapshot_interval=int(args.snapshot_interval),
            history_limit=int(args.history_limit),
        ):
            payload = run_global_balance_scenario(cfg, thresholds=thresholds)
            run_metrics = payload.get("metrics", {}) if isinstance(payload, dict) else {}
            runs.append(
                {
                    "scenario": dict(payload.get("scenario", {})),
                    "behavior_map": dict(run_metrics.get("behavior_map", {})) if isinstance(run_metrics, dict) else {},
                    "survival": dict(run_metrics.get("survival", {})) if isinstance(run_metrics, dict) else {},
                    "camp_proto": dict(run_metrics.get("camp_proto", {})) if isinstance(run_metrics, dict) else {},
                    "settlement_legitimacy": dict(run_metrics.get("settlement_legitimacy", {})) if isinstance(run_metrics, dict) else {},
                }
            )
        artifacts[family] = aggregate_behavior_runs(scenario_family=family, runs=runs)

    mapping = {
        "baseline": "behavior_map_baseline.json",
        "food_stress": "behavior_map_food_stress.json",
        "population_variant": "behavior_map_population_variant.json",
        "reduced_pressure": "behavior_map_reduced_pressure.json",
    }

    written_paths: List[str] = []
    for family, payload in artifacts.items():
        path = out_dir / mapping[family]
        _write_json(path, payload)
        written_paths.append(str(path))

    summary_payload = {
        "run_configuration": {
            "scenario_families": families,
            "seeds": [int(s) for s in args.seeds],
            "ticks": int(args.ticks),
            "snapshot_interval": int(args.snapshot_interval),
            "history_limit": int(args.history_limit),
        },
        "scenario_summaries": {
            family: {
                "run_count": int(payload.get("run_count", 0)),
                "top_activity_types": list(payload.get("top_activity_types", []))[:10],
                "top_task_transitions": list(payload.get("top_task_transitions", []))[:12],
                "secondary_nucleus_lifecycle": dict(payload.get("secondary_nucleus_lifecycle", {})),
                "cluster_population_distribution_summary_avg": dict(payload.get("cluster_population_distribution_summary_avg", {})),
            }
            for family, payload in artifacts.items()
        },
        "written_files": written_paths,
    }
    summary_path = out_dir / "behavior_map_summary.json"
    _write_json(summary_path, summary_payload)

    print("Behavior map validation completed.")
    for path in written_paths:
        print(path)
    print(str(summary_path))


if __name__ == "__main__":
    main()
