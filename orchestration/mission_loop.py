"""Bounded, evidence-driven quality repair inside one isolated Git worktree."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from orchestration.quality import QualityError


class MissionQualityExhausted(RuntimeError):
    """The mission exhausted its allowed correction cycles."""


def repair_failed_quality(
    *,
    verify: Callable[[], dict[str, Any]],
    repair: Callable[[str, int], None],
    checkpoint: Callable[[], None],
    max_repairs: int = 2,
) -> dict[str, Any]:
    """Verify first; repair only deterministic quality failures.

    Persist each attempted repair even if the CLI fails, so partial changes are
    recoverable. No retry for auth, quota, missing tools, or arbitrary failures.
    """
    if isinstance(max_repairs, bool) or not isinstance(max_repairs, int) or not 0 <= max_repairs <= 5:
        raise ValueError("max_repairs must be an integer from 0 to 5")
    failures: list[str] = []
    for attempt in range(max_repairs + 1):
        try:
            evidence = verify()
        except QualityError as exc:
            reason = str(exc)[:400]
            failures.append(reason)
            if attempt == max_repairs:
                raise MissionQualityExhausted(
                    f"Quality gate failed after {attempt} repair(s): {reason}"
                ) from exc
            # Preserve patch changes on either successful or failed CLI calls.
            try:
                repair(reason, attempt + 1)
            finally:
                checkpoint()
        else:
            return {"quality": evidence, "repairs": attempt, "failures": failures}
    raise AssertionError("unreachable")
