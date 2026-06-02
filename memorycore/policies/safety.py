from __future__ import annotations


class SafetyError(ValueError):
    pass


class SafetyPolicy:
    name = "default_safety"

    def validate_decision(
        self,
        *,
        key: str,
        value: str,
        scope: str,
        commit: bool,
    ) -> None:
        if not commit:
            raise SafetyError("decision update requires an explicit commit signal")
        if not key or not value or not scope:
            raise SafetyError("decision update requires key, value, and scope")


def get_safety_policy(name: str | None = None) -> SafetyPolicy:
    if name in {None, "default", "require_commit_for_decision"}:
        return SafetyPolicy()
    raise ValueError(f"unknown safety policy: {name}")
