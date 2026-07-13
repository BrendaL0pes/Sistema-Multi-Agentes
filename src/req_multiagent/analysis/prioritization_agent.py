"""MoSCoW prioritization agent and deterministic ranking helpers."""

from __future__ import annotations

import re

from req_multiagent.config import load_settings
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
        model=Groq(id=settings.model_id),
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
