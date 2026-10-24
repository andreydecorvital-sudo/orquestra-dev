"""Orquestra assistant hub: specialist plans only, never inference or execution.

A trusted executor supplies provider eligibility and role bindings. User text
and model output cannot grant tools, access, credit, or production permissions.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal, Mapping

Intent = Literal["general", "research", "engineering", "design", "marketing",
                 "commerce", "review", "multidisciplinary"]
Action = Literal["answer", "sandbox_edit", "external_action"]

# Named responsibilities, not fictional online agents or hardwired paid providers.
ROLE_DESCRIPTIONS: dict[str, str] = {
    "assistant": "Conversa pessoal, contexto e coordenação",
    "research": "Pesquisa com fontes e verificação de fatos",
    "engineering": "Programação, arquitetura, integração e testes",
    "design": "UX, interfaces, acessibilidade e identidade visual",
    "marketing": "Marketing, conteúdo, anúncios e conversão",
    "commerce": "Marketplaces, catálogo, estoque e operação",
    "review": "Revisão independente de evidências, testes e riscos",
}
INTENT_ROLES: dict[str, tuple[str, ...]] = {
    "general": ("assistant",),
    "research": ("research",),
    "engineering": ("engineering",),
    "design": ("design",),
    "marketing": ("marketing",),
    "commerce": ("commerce",),
    "review": ("review",),
    "multidisciplinary": ("research", "engineering", "design", "review"),
}
SENSITIVE_ACTIONS = frozenset({
    "deploy_production", "merge_pull_request", "modify_live_database",
    "delete_live_data", "send_external_message", "publish_live_listing",
    "change_live_prices", "issue_invoice", "print_shipping_labels",
    "spend_money", "modify_secrets", "change_access_permissions",
})


@dataclass(frozen=True)
class AssistantRequest:
    intent: Intent = "general"
    action: Action = "answer"
    project_id: str | None = None
    complex_work: bool = False


@dataclass(frozen=True)
class SpecialistStep:
    role: str
    provider: str | None
    purpose: str


@dataclass(frozen=True)
class AssistantPlan:
    mode: str
    steps: tuple[SpecialistStep, ...]
    blockers: tuple[str, ...]
    approval_required: bool
    executor_authorized: bool = False
    # Only a request for context, never evidence of GitHub access or inference.
    knowledge_sources: tuple[str, ...] = ()

    @property
    def status(self) -> str:
        return "blocked" if self.blockers else "planned"


def plan_assistance(
    request: AssistantRequest,
    *,
    role_providers: Mapping[str, str],
    connected_providers: frozenset[str],
    authorized_projects: frozenset[str] = frozenset(),
    sandbox_ready: bool = False,
) -> AssistantPlan:
    """Plan a conversation or bounded work using only trusted provider inventory.

    Planning does not dispatch a model, prove entitlement, write files, or start
    a mission. No silent fallback to another provider, paid or otherwise.
    """
    if request.intent not in INTENT_ROLES:
        raise ValueError("Intenção desconhecida")
    if request.action not in {"answer", "sandbox_edit", "external_action"}:
        raise ValueError("Ação desconhecida")
    if not isinstance(request.complex_work, bool):
        raise ValueError("Complexidade inválida")
    if not isinstance(connected_providers, frozenset):
        raise TypeError("Provedores devem ser um conjunto imutável verificado")

    roles = list(INTENT_ROLES[request.intent])
    if request.complex_work and "review" not in roles:
        roles.append("review")
    steps: list[SpecialistStep] = []
    blockers: list[str] = []
    for role in roles:
        provider = role_providers.get(role)
        if not isinstance(provider, str) or not provider:
            blockers.append(f"Especialista {role} não configurada")
            provider = None
        elif provider not in connected_providers:
            blockers.append(f"Provedor {provider} não verificado para {role}")
        steps.append(SpecialistStep(role, provider, ROLE_DESCRIPTIONS[role]))

    if request.action == "sandbox_edit":
        if not request.project_id or request.project_id not in authorized_projects:
            blockers.append("Projeto não autorizado para sandbox")
        if not sandbox_ready:
            blockers.append("Executor isolado não confirmado")
    if request.action == "external_action":
        blockers.append("Efeito externo requer autorização humana específica")
    # Origin is a private knowledge repository, not an LLM/provider or a model.
    # Actual reads require a separate owner-scoped OriginReadGrant and GitHub token.
    use_origin = request.complex_work or request.intent in {
        "research", "engineering", "design", "marketing",
        "commerce", "review", "multidisciplinary",
    }
    return AssistantPlan(
        mode="conversation" if request.action == "answer" else "work",
        steps=tuple(steps), blockers=tuple(blockers),
        approval_required=request.action == "external_action",
        knowledge_sources=("origin",) if use_origin else (),
    )


def may_perform_external_action(operation: str) -> bool:
    """No routing output can authorize a consequential external action."""
    return False
