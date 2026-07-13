"""MoSCoW prioritization agent and deterministic analysis helpers."""

from __future__ import annotations

from req_multiagent.config import load_settings
from req_multiagent.llm_utils import parse_structured_response, run_groq_json
from req_multiagent.models import (
    ConflictFinding,
    Evidence,
    MoscowPriority,
    PriorityAssessment,
    Requirement,
    RequirementType,
)


def create_prioritization_agent():
    """Create the Agno agent responsible for MoSCoW prioritization."""

    from agno.agent import Agent
    from agno.models.groq import Groq

    settings = load_settings()
    return Agent(
        name="MoSCoW Prioritization Analyst",
        role="Assign MoSCoW priority to requirements with rationale.",
        model=Groq(
            id=settings.model_id,
            api_key=settings.groq_api_key,
            timeout=60,
            max_retries=2,
            retries=2,
        ),
        instructions=[
            "Responda em portugues.",
            "Classifique requisitos em Must, Should, Could ou Won't.",
            "Justifique cada prioridade com base em impacto, risco e conflito.",
            "Quando houver conflito nao resolvido, recomende revisao humana.",
        ],
        markdown=True,
    )


def prioritize_requirements(
    requirements: list[Requirement],
    conflicts: list[ConflictFinding] | None = None,
) -> list[PriorityAssessment]:
    """Assign deterministic MoSCoW priorities for validated requirements."""

    conflict_map = {
        conflict.requirement_id: conflict for conflict in conflicts or []
    }
    assessments: list[PriorityAssessment] = []

    for requirement in requirements:
        conflict = conflict_map.get(requirement.id)
        if conflict:
            assessments.append(_build_conflicted_assessment(requirement, conflict))
            continue

        if requirement.type == RequirementType.FUNCTIONAL:
            assessments.append(
                PriorityAssessment(
                    requirement_id=requirement.id,
                    priority=MoscowPriority.MUST,
                    rationale=(
                        "Requisito funcional extraido do fluxo principal; deve "
                        "ser tratado como essencial ate revisao do stakeholder."
                    ),
                    confidence=0.75,
                )
            )
        else:
            assessments.append(
                PriorityAssessment(
                    requirement_id=requirement.id,
                    priority=MoscowPriority.SHOULD,
                    rationale=(
                        "Requisito nao funcional importante para qualidade, mas "
                        "precisa de criterio mensuravel antes de virar Must."
                    ),
                    confidence=0.65,
                    limitations=[
                        "Prioridade pode mudar quando metricas de aceitacao "
                        "forem definidas."
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
    payload = run_groq_json(
        prompt,
        LlmPriorityAssessments,
        "MoSCoW Prioritization Analyst",
        system_instructions=[
            "Responda em portugues.",
            "Classifique requisitos em Must, Should, Could ou Won't.",
            "Justifique cada prioridade com base em impacto, risco e conflito.",
            "Quando houver conflito nao resolvido, recomende revisao humana.",
        ],
        model_id=settings.model_id,
        api_key=settings.groq_api_key,
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
                    explanation="Prioridade sugerida pelo agente Agno/Groq.",
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


def _build_conflicted_assessment(
    requirement: Requirement,
    conflict: ConflictFinding,
) -> PriorityAssessment:
    return PriorityAssessment(
        requirement_id=requirement.id,
        priority=MoscowPriority.WONT,
        rationale=(
            "Requisito possui conflito nao resolvido e deve aguardar decisao "
            "humana antes de entrar no escopo implementavel."
        ),
        evidence=[
            Evidence(
                source=evidence.source,
                excerpt=evidence.excerpt,
                explanation=evidence.explanation,
            )
            for evidence in conflict.evidence
        ],
        confidence=0.8,
        limitations=[
            "Classificacao Won't indica bloqueio temporario por conflito, "
            "nao descarte definitivo."
        ],
    )


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


def _parse_llm_payload(response, schema_type):
    return parse_structured_response(
        response,
        schema_type,
        "MoSCoW Prioritization Analyst",
    )
