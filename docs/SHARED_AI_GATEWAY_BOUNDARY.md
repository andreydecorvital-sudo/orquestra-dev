# Orquestra ↔ Shared AI Gateway: boundary and integration contract

## No change to Orquestra execution semantics

Orquestra's `policies/SUBSCRIPTION_ONLY.md` is mandatory. All **coding / planning / code-review** agent execution stays with authenticated official Codex CLI / Claude Code CLI and Hermes as explicitly permitted. No API-billed OpenAI/Anthropic fallbacks, no reuse of ChatGPT/Claude subscription tokens for HTTP inference, no auto-merge or auto-deploy.

The multi-provider gateway prepared for CRM, Argoplace and MIRA is a **separate SaaS inference plane**. Do not insert provider keys or LiteLLM virtual keys into `gateway/engine.py`, `runner/agent_worker.py`, or `gateway/hermes_bridge.py`. This repository gets only the *read-only integration contract* so that future external research, if separately approved and budgeted, can be handled outside the Orquestra coding executor.

## External research contract (not enabled)

Model alias: `orquestra-research`. Provider set on the gateway: Gemini, OpenAI, Claude, Groq and Grok, with policy-controlled fallbacks. Any external research call would require all of the following:
- A separate research application/service, NOT the Orquestra local subscription runner.
- Explicit authorization to use paid inference, distinct from approval to execute a coding mission.
- A virtual key scoped to `orquestra-research` and monthly request/dollar limits in a dedicated gateway PostgreSQL database.
- Sanitized text only; no repo secrets, checkout contents, patches, production data or subscription tokens sent to the shared gateway.
- No write tools, no Git push, no deployment permissions, no automated decision authority.
- Observable response with model, time and token usage; failure remains `UNAVAILABLE` rather than changing provider silently.

The machine-readable `docs/shared-ai-gateway-contract.json` lists the applicable aliases and explicitly disables execution. Do not mark this integration as operational until a separate billable-research policy is authorized.

## Why not switch the Orquestra itself?

Orquestra's architectural guarantee is *subscription-only*, while an AI API gateway is usage-billed. These are different products and budget/accounting boundaries. A shared provider catalog is possible, but silent runtime unification violates an existing user requirement.
