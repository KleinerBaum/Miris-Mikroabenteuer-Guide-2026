from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.mikroabenteuer.models import ActivityPlan
from src.mikroabenteuer.plan_reports import (
    hash_plan,
    load_plan_reports,
    save_plan_report,
)


def _sample_plan() -> ActivityPlan:
    return ActivityPlan(
        title="Waldspaziergang",
        summary="Kurzer Spaziergang im Park",
        steps=["Start am Eingang", "Blätter sammeln"],
        safety_notes=["Auf Wege achten"],
        parent_child_prompts=["Welche Farbe hat das Blatt?"],
        variants=["Bei Regen Indoor-Basteln"],
    )


def test_save_plan_report_writes_minimal_metadata(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    report_path = tmp_path / "reports.jsonl"
    monkeypatch.setenv("PLAN_REPORTS_PATH", str(report_path))

    report = save_plan_report(_sample_plan(), "Unsicher / Unsafe")

    assert report_path.exists()
    payload = json.loads(report_path.read_text(encoding="utf-8").strip())
    assert set(payload.keys()) == {"timestamp_utc", "plan_hash", "reason"}
    assert payload["reason"] == "Unsicher / Unsafe"
    assert payload["plan_hash"] == report.plan_hash


def test_load_plan_reports_returns_latest_first(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    report_path = tmp_path / "reports.jsonl"
    monkeypatch.setenv("PLAN_REPORTS_PATH", str(report_path))

    plan = _sample_plan()
    save_plan_report(plan, "Unpassend / Not relevant")
    save_plan_report(plan, "Sonstiges / Other")

    reports = load_plan_reports(limit=10)

    assert len(reports) == 2
    assert reports[0]["reason"] == "Sonstiges / Other"
    assert reports[1]["reason"] == "Unpassend / Not relevant"


def test_hash_plan_is_stable_for_same_content() -> None:
    plan = _sample_plan()

    assert hash_plan(plan) == hash_plan(plan.model_copy())
