"""LLM helpers for evolving a requirements project."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from req_multiagent.config import load_settings
from req_multiagent.llm_utils import run_structured_agent
from req_multiagent.models import (
    ConsolidatedReport,
    Requirement,
    RequirementType,
    SourceTrace,
)


class ProjectRequirementPayload(BaseModel):
    """Requirement representation returned by the project update agent."""

    id: str
    description: str
    type: Literal["functional", "non_functional"]
    source_excerpt: str = ""
    change_reason: str = ""


class ProjectRequirementsPayload(BaseModel):
    """Full updated requirement set for a project."""

    assistant_message: str = Field(
        description="Mensagem curta em portugues explicando o que foi alterado."
    )
    requirements: list[ProjectRequirementPayload]


class ProjectAnswerPayload(BaseModel):
    """Answer returned for a project chat question."""

    assistant_message: str


def create_project_update_agent():
    """Create the Agno agent responsible for incremental project updates."""

    from agno.agent import Agent
    from agno.models.groq import Groq

    settings = load_settings()
    return Agent(
        name="Project Update Agent",
        role="Merge new stakeholder conversations into an existing requirements project.",
        model=Groq(
            id=settings.model_id,
            api_key=settings.groq_api_key,
            timeout=60,
            max_retries=2,
            retries=2,
        ),
        instructions=[
            "Responda em portugues.",
            "Atue como analista de Engenharia de Requisitos.",
            "Mantenha o projeto isolado: compare apenas requisitos deste projeto.",
            "Preserve IDs existentes quando atualizar requisito.",
            "Crie novos requisitos apenas quando houver informacao nova.",
            "Retorne sempre o conjunto completo atualizado.",
        ],
        markdown=True,
    )


def create_adjustment_agent():
    """Create the Agno agent responsible for interactive requirement adjustments."""

    from agno.agent import Agent
    from agno.models.groq import Groq

    settings = load_settings()
    return Agent(
        name="Requirements Adjustment Agent",
        role="Apply user instructions to update a requirements project.",
        model=Groq(
            id=settings.model_id,
            api_key=settings.groq_api_key,
            timeout=60,
            max_retries=2,
            retries=2,
        ),
        instructions=[
            "Responda em portugues.",
            "Atue como agente de ajuste de requisitos.",
            "Nao invente escopo fora da solicitacao do usuario.",
            "Preserve rastreabilidade e IDs quando possivel.",
            "Retorne sempre o conjunto completo atualizado.",
        ],
        markdown=True,
    )


def create_chat_agent():
    """Create the Agno agent responsible for project Q&A."""

    from agno.agent import Agent
    from agno.models.groq import Groq

    settings = load_settings()
    return Agent(
        name="Requirements Chat Agent",
        role="Answer questions about the current requirements project.",
        model=Groq(
            id=settings.model_id,
            api_key=settings.groq_api_key,
            timeout=60,
            max_retries=2,
            retries=2,
        ),
        instructions=[
            "Responda em portugues.",
            "Atue como assistente conversacional de Engenharia de Requisitos.",
            "Responda perguntas sem modificar o projeto.",
            "Se o usuario pedir uma alteracao, oriente a escrever como comando.",
        ],
        markdown=True,
    )


def merge_incremental_conversation(
    current_requirements: list[Requirement],
    new_requirements: list[Requirement],
    transcript_text: str,
    source_name: str,
) -> tuple[list[Requirement], str]:
    """Merge newly extracted requirements into the current project set."""

    settings = load_settings()
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY nao configurada para usar a LLM.")

    prompt = (
        "Atualize o conjunto de requisitos de um projeto de Engenharia de "
        "Requisitos usando uma nova conversa incremental. Preserve IDs de "
        "requisitos existentes quando a conversa apenas detalhar ou corrigir "
        "algo. Crie novo ID somente para requisito realmente novo. Nao duplique "
        "requisitos semanticamente equivalentes.\n\n"
        f"Requisitos atuais:\n{_requirements_prompt(current_requirements)}\n\n"
        f"Requisitos candidatos extraidos da nova conversa:\n"
        f"{_requirements_prompt(new_requirements)}\n\n"
        f"Nova conversa completa ({source_name}):\n{transcript_text}"
    )
    payload = run_structured_agent(
        create_project_update_agent(),
        prompt,
        ProjectRequirementsPayload,
        "Project Update Agent",
    )
    return (
        _payload_to_requirements(
            payload.requirements,
            current_requirements=current_requirements,
            source_name=source_name,
        ),
        payload.assistant_message,
    )


def adjust_requirements_from_instruction(
    current_requirements: list[Requirement],
    instruction: str,
) -> tuple[list[Requirement], str]:
    """Apply a user adjustment instruction to the project requirements."""

    settings = load_settings()
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY nao configurada para usar a LLM.")

    prompt = (
        "Aplique a solicitacao do usuario ao conjunto de requisitos do projeto. "
        "Voce pode reescrever, reclassificar, unir, remover ou adicionar "
        "requisitos quando a instrucao justificar. Preserve IDs sempre que a "
        "mudanca for uma atualizacao do mesmo requisito. Retorne o conjunto "
        "completo atualizado.\n\n"
        f"Requisitos atuais:\n{_requirements_prompt(current_requirements)}\n\n"
        f"Solicitacao do usuario:\n{instruction}"
    )
    payload = run_structured_agent(
        create_adjustment_agent(),
        prompt,
        ProjectRequirementsPayload,
        "Requirements Adjustment Agent",
    )
    return (
        _payload_to_requirements(
            payload.requirements,
            current_requirements=current_requirements,
            source_name="ajuste_interativo",
        ),
        payload.assistant_message,
    )


def answer_project_question(report: ConsolidatedReport, question: str) -> str:
    """Answer a user question about the current project without changing it."""

    settings = load_settings()
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY nao configurada para usar a LLM.")

    prompt = (
        "Responda a pergunta do usuario sobre o projeto de requisitos atual. "
        "Nao altere requisitos, nao crie novos itens e nao retorne operacoes. "
        "Explique com base apenas no estado atual do projeto.\n\n"
        f"Requisitos:\n{_requirements_prompt(report.requirements)}\n\n"
        f"Ambiguidades:\n{_ambiguities_prompt(report)}\n\n"
        f"Conflitos:\n{_conflicts_prompt(report)}\n\n"
        f"Prioridades:\n{_priorities_prompt(report)}\n\n"
        f"Pergunta do usuario:\n{question}"
    )
    payload = run_structured_agent(
        create_chat_agent(),
        prompt,
        ProjectAnswerPayload,
        "Requirements Chat Agent",
    )
    return payload.assistant_message


def _payload_to_requirements(
    payload_items: list[ProjectRequirementPayload],
    current_requirements: list[Requirement],
    source_name: str,
) -> list[Requirement]:
    current_by_id = {
        requirement.id: requirement for requirement in current_requirements
    }
    used_ids: set[str] = set()
    next_number = _next_requirement_number(current_requirements)
    prefix = _project_prefix(current_requirements)
    requirements: list[Requirement] = []

    for item in payload_items:
        requirement_id = item.id.strip()
        if not requirement_id or requirement_id in used_ids:
            requirement_id = f"{prefix}-{next_number:03d}"
            next_number += 1
        used_ids.add(requirement_id)

        existing = current_by_id.get(requirement_id)
        excerpt = item.source_excerpt.strip() or item.description.strip()
        source = (
            existing.source
            if existing and not item.source_excerpt.strip()
            else SourceTrace(source_path=source_name, excerpt=excerpt)
        )
        requirements.append(
            Requirement(
                id=requirement_id,
                title=_build_title(item.description),
                description=item.description.strip(),
                type=RequirementType(item.type),
                source=source,
                acceptance_criteria=(
                    existing.acceptance_criteria if existing else []
                ),
                tags=existing.tags if existing else [],
                metadata={
                    **(existing.metadata if existing else {}),
                    "last_change_reason": item.change_reason,
                },
            )
        )

    return requirements


def _requirements_prompt(requirements: list[Requirement]) -> str:
    if not requirements:
        return "- Nenhum requisito atual."
    return "\n".join(
        f"- {item.id} ({item.type.value}): {item.description}"
        for item in requirements
    )


def _ambiguities_prompt(report: ConsolidatedReport) -> str:
    if not report.ambiguities:
        return "- Nenhuma ambiguidade."
    return "\n".join(
        f"- {item.requirement_id}: termo '{item.term}' - {item.explanation}"
        for item in report.ambiguities
    )


def _conflicts_prompt(report: ConsolidatedReport) -> str:
    if not report.conflicts:
        return "- Nenhum conflito."
    return "\n".join(
        f"- {item.requirement_id} x {item.conflicting_requirement_id}: "
        f"{item.explanation}"
        for item in report.conflicts
    )


def _priorities_prompt(report: ConsolidatedReport) -> str:
    if not report.priorities:
        return "- Nenhuma prioridade."
    return "\n".join(
        f"- {item.requirement_id}: {item.priority.value} - {item.rationale}"
        for item in report.priorities
    )


def _next_requirement_number(requirements: list[Requirement]) -> int:
    numbers = []
    for requirement in requirements:
        suffix = requirement.id.rsplit("-", maxsplit=1)[-1]
        if suffix.isdigit():
            numbers.append(int(suffix))
    return max(numbers, default=0) + 1


def _project_prefix(requirements: list[Requirement]) -> str:
    if not requirements:
        return "REQ"
    first_id = requirements[0].id
    if "-" not in first_id:
        return "REQ"
    return first_id.rsplit("-", maxsplit=1)[0]


def _build_title(description: str) -> str:
    words = description.rstrip(".").split()
    return " ".join(words[:8]) or "Requisito"
