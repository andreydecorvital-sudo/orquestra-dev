# Orquestra — Engineering quality bar

Orquestra learns from the public designs of Superpowers (structured plans and
verification), Symphony (durable task execution) and Orchestrator.inc (multiple
agents). This original policy is NOT a fork or runtime installation of them.

## Mandatory pre-review evidence

- Authorized isolated worktree, no production change.
- Git patch saved locally BEFORE the Claude reviewer is called.
- git diff --check and Python/JavaScript syntax checks where available.
- Risky paths (workflows, migrations, env configs and lockfiles) flagged for approval.
- Test suite marked NOT RUN unless an actual test command was executed.
- Security audit marked NOT RUN unless an actual independent scan was executed.
- Claude reviews in a joint task; failure preserves the patch but blocks completion.
- Human approval required for merge, deployment, API credential access and production operations.

The checker at orchestration/quality.py does not run arbitrary project code or
model API calls. It is a first-pass quality gate, not proof of functional correctness.

## Explicitly incomplete until provisioned

A dedicated Supabase queue, properly authenticated cloud worker and official
Codex/Claude login sessions are still required for real 24/7 execution. Hermes
is optional; it has not been installed. Do not confuse durable queue storage
with infinite usage of AI subscriptions.
