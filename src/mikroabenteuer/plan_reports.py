from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import ActivityPlan


REPORT_REASONS: tuple[str, ...] = (
    "Unsicher / Unsafe",
    "Unpassend / Not relevant",
    "Faktisch falsch / Factually wrong",
    "Sonstiges / Other",
)


@dataclass(frozen=True)
class PlanReport:
    timestamp_utc: str
    plan_hash: str
    reason: str


def _report_store_path() -> Path:
    configured = os.getenv("PLAN_REPORTS_PATH", "")
    if configured.strip():
        return Path(configured).expanduser()
    return Path("data") / "plan_reports.jsonl"


def hash_plan(plan: ActivityPlan) -> str:
    canonical = json.dumps(
        plan.model_dump(mode="json"), ensure_ascii=False, sort_keys=True
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def save_plan_report(plan: ActivityPlan, reason: str) -> PlanReport:
    normalized_reason = reason.strip()
    if not normalized_reason:
        raise ValueError("reason must not be empty")

    report = PlanReport(
        timestamp_utc=datetime.now(tz=timezone.utc).isoformat(),
        plan_hash=hash_plan(plan),
        reason=normalized_reason,
    )

    path = _report_store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp_utc": report.timestamp_utc,
        "plan_hash": report.plan_hash,
        "reason": report.reason,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    return report


def load_plan_reports(limit: int = 50) -> list[dict[str, Any]]:
    path = _report_store_path()
    if not path.exists():
        return []

    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            rows.append(cast_report_json(json.loads(stripped)))

    return rows[-max(0, limit) :][::-1]


def cast_report_json(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        "timestamp_utc": str(value.get("timestamp_utc", "")),
        "plan_hash": str(value.get("plan_hash", "")),
        "reason": str(value.get("reason", "")),
    }
