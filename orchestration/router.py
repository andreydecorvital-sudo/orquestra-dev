"""Deterministic routing plan, NO network calls, no agents launched.

Roles are provider-agnostic. Only official, authorized adapters may run each role.
The pipeline should persist each stage, be idempotent, and require a separate
permissioned executor to perform any real work.
"""
from dataclasses import dataclass, asdict
from typing import Literal

WorkType = Literal['design', 'code', 'mixed', 'investigation', 'research']
Complexity = Literal['low', 'medium', 'high', 'unknown']
Risk = Literal['low', 'medium', 'high']
Mode = Literal['auto', 'gpt', 'claude', 'joint']

@dataclass(frozen=True)
class Stage:
    role: str
    action: str
    must_pass: bool = True
    approval_required: bool = False

@dataclass(frozen=True)
class Assignment:
    strategy: str
    lead: str
    supporting: tuple[str, ...]
    stages: tuple[Stage, ...]
    approval_before_execute: bool
    approval_before_merge: bool
    status: str
    reason: str
    provider_runnable: bool


def route(*, work_type: WorkType, complexity: Complexity = 'medium',
          risk: Risk = 'low', mode: Mode = 'auto',
          gpt_available: bool = True, claude_available: bool = True,
          needs_implementation: bool = True) -> Assignment:
    """Plan stages and gates; DOES NOT schedule or call an AI provider.

    High-risk actions need explicit approval before any execution. Repo writes,
    deployments and production actions must be additionally authorized by
    their individual adapters. Reaching `human.approve` is not authorization.
    """
    if work_type not in {'design', 'code', 'mixed', 'investigation', 'research'}:
        raise ValueError('work_type inválido')
    if complexity not in {'low', 'medium', 'high', 'unknown'}:
        raise ValueError('complexity inválida')
    if risk not in {'low', 'medium', 'high'}:
        raise ValueError('risk inválido')
    if mode not in {'auto', 'gpt', 'claude', 'joint'}:
        raise ValueError('mode inválido')

    critical = risk == 'high'
    uncertain = complexity in {'high', 'unknown'}
    joint = mode == 'joint' or (mode == 'auto' and (
        work_type in {'mixed', 'investigation'} or uncertain or critical))
    chosen = 'joint' if joint else (mode if mode != 'auto' else
        ('claude' if work_type == 'design' else 'gpt' if work_type == 'code'
         else 'support'))
    stages = []
    def add(role: str, action: str, *, approval=False):
        stages.append(Stage(role, action, approval_required=approval))

    if critical:
        add('human', 'aprovar escopo antes de execução', approval=True)
    if work_type in {'investigation', 'research', 'mixed'} or uncertain:
        add('support', 'reunir evidências e documentação')

    if work_type == 'research':
        add('support', 'produzir relatório com fontes')
        add('qa', 'checar evidências e links')
    elif chosen == 'joint':
        if work_type in {'design', 'mixed'}:
            add('claude', 'definir UX, layout e critérios visuais')
        elif work_type == 'investigation':
            add('gpt', 'investigar hipótese inicial em isolamento')
            add('claude', 'investigar hipótese independente; não copiar a primeira')
            add('support', 'consolidar evidências e diferenças')
        else:
            add('claude', 'revisar proposta e riscos antes da implementação')
        if work_type != 'investigation' and needs_implementation:
            add('gpt', 'implementar código em branch isolada')
        elif work_type == 'investigation' and needs_implementation:
            add('gpt', 'implementar correção após investigação')
        add('qa', 'rodar testes objetivos, lint e segurança')
        add('claude', 'revisar alteração e critérios de aceitação')
    elif chosen == 'claude':
        add('claude', 'produzir design e especificação de aceite' if work_type == 'design'
            else 'trabalhar na tarefa atribuída')
        if needs_implementation:
            add('gpt', 'implementar especificação de design em branch isolada')
        add('qa', 'verificar critérios de qualidade')
    elif chosen == 'gpt':
        add('gpt', 'implementar em branch isolada')
        add('qa', 'rodar testes, lint e segurança')
        if uncertain or risk == 'medium':
            add('claude', 'revisar áreas sensíveis e arquitetura')
    else:
        add('support', 'organizar pesquisa e contexto')
        add('qa', 'verificar fontes e saídas')

    add('human', 'aprovar PR e publicação; nunca publicar automaticamente', approval=True)
    requested = {s.role for s in stages}
    missing = sorted(r for r, available in (('gpt', gpt_available), ('claude', claude_available))
                     if r in requested and not available)
    lead = 'claude' if chosen == 'claude' else ('support' if chosen == 'support' else 'gpt')
    if chosen == 'joint' and work_type in {'design','mixed'}:
        lead = 'claude'
    return Assignment(
        strategy=chosen,
        lead=lead,
        supporting=tuple(sorted(requested - {lead, 'human'})),
        stages=tuple(stages),
        approval_before_execute=critical,
        approval_before_merge=True,
        status='blocked' if missing else 'planned',
        reason=('Conector autorizado ausente: ' + ', '.join(missing)) if missing else
               ('Revisão conjunta por complexidade/risco' if joint else
                'Especialização preferida com validação'),
        provider_runnable=False,  # Nothing may start based on a routing plan alone.
    )


def as_dict(assignment: Assignment):
    return asdict(assignment)
