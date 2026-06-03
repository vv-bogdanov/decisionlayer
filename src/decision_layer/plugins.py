from __future__ import annotations

from typing import Protocol

from decision_layer.core import DecisionBrief, DecisionState
from decision_layer.extraction import DecisionCommand, SourceMessage


class ExtractorPlugin(Protocol):
    def extract(self, message: SourceMessage) -> tuple[DecisionCommand, ...]:
        """Return decision commands proposed from an authorized source message."""


class StorePlugin(Protocol):
    def load(self) -> DecisionState:
        """Load active decisions."""

    def save(self, state: DecisionState) -> None:
        """Persist active decisions outside the pure core."""


class BriefPlugin(Protocol):
    def build(self, state: DecisionState, task_context: str) -> DecisionBrief:
        """Build prompt enrichment from active decisions."""
