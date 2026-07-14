"""MoSCoW prioritization agent and deterministic ranking helpers."""

from __future__ import annotations

import re

from req_multiagent.config import load_settings
from req_multiagent.llm_utils import run_structured_agent
from req_multiagent.models import (
    AmbiguityFinding,
    ConflictFinding,
    Evidence,
    MoscowPriority,
    PriorityAssessment,
    Requirement,
    RequirementType,
)

MUST_SIGNALS = (
    "finalizar",
    "bloquear",
    "notificar",
)
SHOULD_SIGNALS = (
    "registrar",
    "exibir",
    "editar",
    "cancelar",
    "sugerir",
)


def create_prioritization_agent():
    """Create the Agno agent responsible for MoSCoW prioritization.

    The import is intentionally lazy so tests that exercise deterministic
    ranking do not require installed model-provider packages or API keys.
    """

    from agno.agent import Agent
    from agno.models.groq import Groq

    settings = load_settings()
    return Agent(
        name="Prioritization Analyst",
        role="Assign MoSCoW priorities to validated requirements.",
        model=Groq(
            id=settings.model_id,
            api_key=settings.groq_api_key,
            timeout=60,
            max_retries=2,
            retries=2,
        ),
        instructions=[
            "Responda em portugues.",
            "Classifique requisitos validados usando MoSCoW: must, should, could, wont.",
            "Rebaixe requisitos ambiguos ou conflitantes de forma justificada.",
            "Priorize fluxos criticos de negocio como must quando estiverem claros.",
            "Explique a razao de cada prioridade de forma objetiva.",
        ],
        markdown=True,
    )


def prioritize_requirements(
    requirements: list[Requirement],
    ambiguities: list[AmbiguityFinding] | None = None,
    conflicts: list[ConflictFinding] | None = None,
) -> list[PriorityAssessment]:
    """Assign MoSCoW priorities to requirements already reviewed by analysis."""

    ambiguous_ids = _collect_requirement_ids(ambiguities or [], "requirement_id")
    conflicting_ids = _collect_requirement_ids(conflicts or [], "requirement_id")
    assessments: list[PriorityAssessment] = []

    for requirement in requirements:
        priority, rationale = _assess_priority(
            requirement=requirement,
            has_ambiguity=requirement.id in ambiguous_ids,
            has_conflict=requirement.id in conflicting_ids,
        )
        assessments.append(
            PriorityAssessment(
                requirement_id=requirement.id,
                priority=priority,
                rationale=rationale,
                evidence=[
                    Evidence(
                        source=requirement.source.source_path,
                        excerpt=requirement.description,
                        explanation="Requisito avaliado para priorizacao MoSCoW.",
                    )
                ],
            )
        )

    return assessments


def prioritize_requirements_with_llm(
    requirements: list[Requirement],
    conflicts: list[ConflictFinding] | None = None,
) -> list[PriorityAssessment]:
    """Assign MoSCoW priorities using the configured Agno LLM agent."""

    settings = load_settings()
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY nao configurada para usar a LLM.")

    from pydantic import BaseModel, Field

    class LlmPriorityAssessment(BaseModel):
        requirement_id: str
        priority: str = Field(pattern="^(must|should|could|wont)$")
        rationale: str
        confidence: float | None = None
        limitations: list[str] = []

    class LlmPriorityAssessments(BaseModel):
        priorities: list[LlmPriorityAssessment]

    prompt = (
        "Priorize os requisitos usando MoSCoW. Considere impacto no fluxo, "
        "risco, dependencia e conflitos. Use wont quando houver conflito "
        "bloqueante ou requisito fora do escopo imediato.\n\n"
        f"Requisitos:\n{_requirements_prompt(requirements)}\n\n"
        f"Conflitos:\n{_conflicts_prompt(conflicts or [])}"
    )
    payload = run_structured_agent(
        create_prioritization_agent(),
        prompt,
        LlmPriorityAssessments,
        "MoSCoW Prioritization Analyst",
    )

    return [
        PriorityAssessment(
            requirement_id=item.requirement_id,
            priority=MoscowPriority(item.priority),
            rationale=item.rationale,
            evidence=[
                Evidence(
                    source="llm:prioritization_agent",
                    excerpt=item.requirement_id,
                    explanation="Prioridade sugerida pelo agente Agno.",
                )
            ],
            confidence=item.confidence,
            limitations=[
                *item.limitations,
                "Prioridade gerada por LLM e deve ser revisada por stakeholders.",
            ],
        )
        for item in payload.priorities
    ]


def _assess_priority(
    requirement: Requirement,
    has_ambiguity: bool,
    has_conflict: bool,
) -> tuple[MoscowPriority, str]:
    if has_conflict:
        return (
            MoscowPriority.WONT,
            "O requisito possui conflito com a base existente ou com o lote atual.",
        )

    if has_ambiguity:
        return (
            MoscowPriority.COULD,
            "O requisito contem termos vagos e deve ser clarificado antes de promocao.",
        )

    if requirement.type == RequirementType.NON_FUNCTIONAL:
        return (
            MoscowPriority.SHOULD,
            "Atributo de qualidade relevante, mas secundario aos fluxos funcionais criticos.",
        )

    if _contains_any_signal(requirement.description, MUST_SIGNALS):
        return (
            MoscowPriority.MUST,
            "Requisito funcional central para o fluxo de negocio descrito na transcricao.",
        )

    if _contains_any_signal(requirement.description, SHOULD_SIGNALS):
        return (
            MoscowPriority.SHOULD,
            "Requisito funcional importante, mas nao bloqueia o fluxo principal sozinho.",
        )

    return (
        MoscowPriority.COULD,
        "Requisito funcional complementar sem sinal claro de criticidade.",
    )


def _collect_requirement_ids(
    findings: list[AmbiguityFinding] | list[ConflictFinding],
    field_name: str,
) -> set[str]:
    return {getattr(finding, field_name) for finding in findings}


def _contains_any_signal(text: str, signals: tuple[str, ...]) -> bool:
    normalized = _normalize_text(text)
    if any(signal in normalized for signal in signals):
        return True

    tokens = re.findall(r"[\w]+", normalized)
    for signal in signals:
        stem = signal[: min(len(signal), 6)]
        if any(token.startswith(stem) for token in tokens):
            return True

    return False


def _normalize_text(text: str) -> str:
    normalized = text.lower()
    normalized = normalized.replace("ã", "a").replace("á", "a").replace("é", "e")
    normalized = normalized.replace("í", "i").replace("ó", "o").replace("ú", "u")
    normalized = normalized.replace("ç", "c")
    return normalized


def _requirements_prompt(requirements: list[Requirement]) -> str:
    return "\n".join(
        f"- {item.id} ({item.type.value}): {item.description}"
        for item in requirements
    )


def _conflicts_prompt(conflicts: list[ConflictFinding]) -> str:
    if not conflicts:
        return "- Nenhum conflito informado."
    return "\n".join(
        f"- {item.requirement_id} x {item.conflicting_requirement_id}: "
        f"{item.explanation}"
        for item in conflicts
    )
