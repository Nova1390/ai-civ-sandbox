from __future__ import annotations

import importlib.util
import json
import sys
import uuid
from pathlib import Path

import pytest


def _load_runner_module() -> object:
    module_path = Path("scripts/run_parameter_sweep.py")
    module_name = f"run_parameter_sweep_test_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_incremental_outputs_persist_on_interruption(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = _load_runner_module()
    out_dir = tmp_path / "sweep_partial"
    call_count = 0
    original_summarize = runner.summarize_family_aggregate

    def interrupting_summarize(aggregate: dict) -> dict:
        nonlocal call_count
        call_count += 1
        # With reduced pressure enabled, this is the first family of config #2.
        if call_count == 5:
            raise RuntimeError("intentional interruption after first completed config")
        return original_summarize(aggregate)

    monkeypatch.setattr(runner, "summarize_family_aggregate", interrupting_summarize)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_parameter_sweep.py",
            "--out-dir",
            str(out_dir),
            "--max-configs",
            "2",
            "--ticks",
            "1",
            "--seeds",
            "4242",
            "--include-reduced-pressure",
            "--dry-run",
        ],
    )

    with pytest.raises(RuntimeError, match="intentional interruption"):
        runner.main()

    results_path = out_dir / "breakeven_sweep_results.json"
    ranked_path = out_dir / "breakeven_ranked_configs.json"
    candidates_path = out_dir / "breakeven_candidate_configs.json"
    assert results_path.exists()
    assert ranked_path.exists()
    assert candidates_path.exists()

    results_payload = json.loads(results_path.read_text())
    assert int(results_payload["summary"]["results_count"]) == 1
    assert [c["config_id"] for c in results_payload["configs"]] == ["baseline_reference"]

    ranked_payload = json.loads(ranked_path.read_text())
    assert int(ranked_payload["summary"]["results_count"]) == 1
    assert [c["config_id"] for c in ranked_payload["ranked_configs"]] == ["baseline_reference"]

    candidates_payload = json.loads(candidates_path.read_text())
    assert int(candidates_payload["summary"]["results_count"]) == 1
    assert isinstance(candidates_payload["candidate_configs"], list)


def test_incremental_rankings_update_each_completed_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = _load_runner_module()
    out_dir = tmp_path / "sweep_full"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_parameter_sweep.py",
            "--out-dir",
            str(out_dir),
            "--max-configs",
            "2",
            "--ticks",
            "1",
            "--seeds",
            "4242",
            "--include-reduced-pressure",
            "--dry-run",
        ],
    )

    runner.main()

    results_payload = json.loads((out_dir / "breakeven_sweep_results.json").read_text())
    ranked_payload = json.loads((out_dir / "breakeven_ranked_configs.json").read_text())
    candidates_payload = json.loads((out_dir / "breakeven_candidate_configs.json").read_text())

    # baseline_reference + 2 sampled configs
    assert int(results_payload["summary"]["results_count"]) == 3
    assert len(results_payload["configs"]) == 3
    assert len(ranked_payload["ranked_configs"]) == 3
    assert int(ranked_payload["summary"]["results_count"]) == 3
    assert int(candidates_payload["summary"]["results_count"]) == 3
