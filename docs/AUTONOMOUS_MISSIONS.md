# Autonomous Missions — autonomy by default, evidence before success

## User contract

One objective is enough. Agents should infer *minor*, reversible details using
the project's existing conventions, repository evidence, and Project Brain.
Never interrupt to ask for obvious steps such as reading docs, retrying a local
syntax error, or selecting an already-standard implementation pattern.

When a material assumption affects pricing, deployment, third parties,
security, real customer data, or other irreversible effects, stop that one
action and request specific human approval. Do not pretend to have approval.

## Trusted action policy

`orchestration/autonomy.py` enumerates automatic and protected operations.
Unknown action IDs fail closed. Only trusted code may classify operations:
an agent's prompt or tool output must not grant itself new permissions.

Automatic actions only apply inside an authorized isolated worktree with
allowlisted tooling. The existing subscription-only policy still applies.
Never bypass provider quotas, authentication, or confirmation boundaries.

## Quality repair v1

The gateway may repair **deterministic QualityError failures**, up to two
additional Codex attempts, within one task. Each repair is saved as a local
patch before the next check, including on a failed CLI invocation. Only
successful checks may move on to independent review.

This is a narrow local loop, not full unattended operations. It does NOT
run the complete application's tests, independently evaluate business goals,
resume a repaired worktree across worker crashes, or deploy code. The existing
job queue and heartbeat still handle worker assignment, not full mission
continuation.

## Follow-on milestones

1. Persist goals, acceptance criteria, checkpoints and per-cycle evidence in
   a dedicated Orquestra database schema; stop repetitive unsuccessful loops.
2. Introduce allowlisted project-specific tests and browser screenshots.
3. Add independent goal verification distinct from the implementing agent.
4. Restore unfinished mission worktrees across crashes with idempotent steps.
5. Prepare feature-branch PRs automatically; keep merge, production, live
   marketplace actions and secrets behind explicit human permission.
6. Integrate Project Brain context with evidence-backed changes and incidents.

A mission is **done** only when its acceptance tests actually pass. Otherwise
return blocked/exhausted with exact evidence and next safe action. No fake
"completed" status and no constant requests for "próximo".
