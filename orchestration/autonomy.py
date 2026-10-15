"""Explicit action policy: automatic safe work; human approval for consequential actions.

The LLM must NOT choose the action's risk classification itself. The caller must
pass a known operation identifier obtained from the trusted executor.
"""
from __future__ import annotations

from dataclasses import dataclass

AUTO_ACTIONS = frozenset({
    "read_repository",
    "read_project_context",
    "inspect_logs",
    "plan_mission",
    "choose_minor_default",
    "edit_isolated_worktree",
    "run_allowlisted_checks",
    "repair_isolated_worktree",
    "save_local_patch",
    "produce_report",
})

PROTECTED_ACTIONS = frozenset({
    "merge_pull_request",
    "deploy_production",
    "modify_live_database",
    "delete_live_data",
    "change_live_prices",
    "publish_live_listing",
    "send_external_message",
    "issue_invoice",
    "print_shipping_labels",
    "spend_money",
    "modify_secrets",
    "install_unreviewed_remote_code",
    "change_access_permissions",
})


@dataclass(frozen=True)
class AutonomyDecision:
    action: str
    status: str  # auto, approval_required, or blocked
    reason: str

    @property
    def may_execute(self) -> bool:
        return self.status == "auto"


def decide_action(
    action: str,
    *,
    authorized_project: bool,
    isolated_environment: bool,
    elevated_risk: bool = False,
) -> AutonomyDecision:
    """Fail closed on unknown actions or unsafe contexts.

    The caller, NOT the model, must verify project allowlists, environment and
    risk flags. A general mission approval never authorizes protected actions.
    """
    if action not in AUTO_ACTIONS | PROTECTED_ACTIONS:
        return AutonomyDecision(action, "blocked", "Unknown operation; cannot infer permission.")
    if not authorized_project:
        return AutonomyDecision(action, "blocked", "Project not in the executor allowlist.")
    if action in PROTECTED_ACTIONS:
        return AutonomyDecision(action, "approval_required", "Consequence outside the isolated workspace.")
    if not isolated_environment or elevated_risk:
        return AutonomyDecision(action, "approval_required", "Operation needs scoped review.")
    return AutonomyDecision(action, "auto", "Reversible, authorized, isolated operation.")
