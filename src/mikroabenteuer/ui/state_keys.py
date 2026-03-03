from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

CriteriaNamespace = Literal["daily", "events"]

_SESSION_PREFIX_BY_NAMESPACE: dict[CriteriaNamespace, str] = {
    "daily": "sidebar",
    "events": "form",
}


@dataclass(frozen=True, slots=True)
class CriteriaKeySpace:
    namespace: CriteriaNamespace

    @property
    def session_prefix(self) -> str:
        return _SESSION_PREFIX_BY_NAMESPACE[self.namespace]

    def widget(self, field: str) -> str:
        return f"{self.session_prefix}_{field}"
