"""Conflict detection agent and deterministic analysis helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from req_multiagent.config import load_settings
from req_multiagent.llm_utils import parse_structured_response, run_groq_json
from req_multiagent.models import (
    ConflictFinding,
    Evidence,
    FindingSeverity,
    Requirement,
)

DEFAULT_EXISTING_REQUIREMENTS_PATH = Path(
    "data/existing_requirements/existing_requirements.md"
)


@dataclass(frozen=True)
class ExistingRequirement:
    """Requirement already approved in the project baseline."""

    id: str
    title: str
    description: str
    source_path: str


def create_conflict_agent():
    """Create the Agno agent responsible for conflict analysis."""

    from agno.agent import Agent
    from agno.models.groq import Groq

    settings = load_settings()
    return Agent(
        name="Conflict Analyst",
        role="Compare new requirements against existing requirements.",
        model=Groq(
            id=settings.model_id,
            api_key=settings.groq_api_key,
            timeout=60,
            max_retries=2,
            retries=2,
        ),
        instructions=[
            "Responda em portugues.",
            "Identifique contradicoes entre requisitos novos e existentes.",
            "Informe IDs conflitantes e explique objetivamente a contradicao.",
            "Quando nao houver evidencias suficientes, recomende revisao humana.",
        ],
        markdown=True,
    )


def load_existing_requirements(
    path: Path | str | None = None,
) -> list[ExistingRequirement]:
    """Load existing requirements from the repository baseline file."""

    requirements_path = Path(path) if path else DEFAULT_EXISTING_REQUIREMENTS_PATH
    content = requirements_path.read_text(encoding="utf-8")
    blocks = re.split(r"\n(?=##\s+REQ-)", content)
    requirements: list[ExistingRequirement] = []

    for block in blocks:
        header = re.search(r"##\s+(REQ-[\w-]+):\s*(.+)", block)
        description = re.search(r"Descrição:\s*(.+)", block)
        if not header or not description:
            continue

        requirements.append(
            ExistingRequirement(
                id=header.group(1).strip(),
                title=header.group(2).strip(),
                description=description.group(1).strip(),
                source_path=requirements_path.as_posix(),
            )
        )

    return requirements


def detect_conflicts(
    requirements: list[Requirement],
    existing_requirements_path: Path | str | None = None,
    compare_existing: bool = True,
) -> list[ConflictFinding]:
    """Detect conflicts against existing requirements and current batch."""

    existing_requirements = (
        load_existing_requirements(existing_requirements_path)
        if compare_existing
        else []
    )
    findings: list[ConflictFinding] = []

    for requirement in requirements:
        for existing_requirement in existing_requirements:
            if _is_conflicting(
                requirement.description,
                existing_requirement.description,
            ):
                findings.append(
                    _build_existing_conflict(requirement, existing_requirement)
                )

    findings.extend(_detect_batch_conflicts(requirements))
    return findings


def detect_conflicts_with_llm(
    requirements: list[Requirement],
    existing_requirements_path: Path | str | None = None,
) -> list[ConflictFinding]:
    """Detect conflicts inside a project, optionally including a baseline file."""

    settings = load_settings()
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY nao configurada para usar a LLM.")

    from pydantic import BaseModel, Field

    class LlmConflictFinding(BaseModel):
        requirement_id: str
        conflicting_requirement_id: str
        explanation: str
        severity: str = Field(pattern="^(low|medium|high)$")
        confidence: float | None = None

    class LlmConflictFindings(BaseModel):
        findings: list[LlmConflictFinding]

    existing_requirements = (
        load_existing_requirements(existing_requirements_path)
        if existing_requirements_path
        else []
    )
    valid_ids = {
        *[requirement.id for requirement in requirements],
        *[requirement.id for requirement in existing_requirements],
    }
    prompt = (
        "Compare os requisitos do projeto entre si"
        + (" e tambem com requisitos existentes" if existing_requirements else "")
        + ". "
        "Retorne somente conflitos reais, citando IDs existentes na entrada. "
        "Conflito significa contradicao objetiva: um requisito permite algo que "
        "outro proibe, exige comportamento incompatível, ou define regra que nao "
        "pode coexistir com a outra. Nao marque como conflito quando o requisito "
        "novo apenas detalha, reforca, complementa ou implementa um requisito "
        "existente. Quando nao houver contradicao objetiva, nao retorne achado.\n\n"
        f"Requisitos do projeto:\n{_requirements_prompt(requirements)}\n\n"
        "Requisitos existentes opcionais:\n"
        f"{_existing_requirements_prompt(existing_requirements)}"
    )
    payload = run_groq_json(
        prompt,
        LlmConflictFindings,
        "Conflict Analyst",
        system_instructions=[
            "Responda em portugues.",
            "Identifique contradicoes entre requisitos novos e existentes.",
            "Informe IDs conflitantes e explique objetivamente a contradicao.",
            "Quando nao houver evidencias suficientes, recomende revisao humana.",
        ],
        model_id=settings.model_id,
        api_key=settings.groq_api_key,
    )

    findings = [
        item for item in payload.findings
        if _is_valid_llm_conflict(item, valid_ids)
    ]
    return [
        ConflictFinding(
            requirement_id=item.requirement_id,
            conflicting_requirement_id=item.conflicting_requirement_id,
            explanation=item.explanation,
            severity=FindingSeverity(item.severity),
            evidence=[
                Evidence(
                    source="llm:conflict_agent",
                    excerpt=(
                        f"{item.requirement_id} x "
                        f"{item.conflicting_requirement_id}"
                    ),
                    explanation="Conflito identificado pelo agente Agno/Groq.",
                )
            ],
            confidence=item.confidence,
            limitations=["Achado gerado por LLM e deve ser revisado por humano."],
        )
        for item in findings
    ]


def _detect_batch_conflicts(requirements: list[Requirement]) -> list[ConflictFinding]:
    findings: list[ConflictFinding] = []
    for index, requirement in enumerate(requirements):
        for other_requirement in requirements[index + 1 :]:
            if _is_conflicting(requirement.description, other_requirement.description):
                findings.append(_build_batch_conflict(requirement, other_requirement))
    return findings


def _is_conflicting(left: str, right: str) -> bool:
    left_normalized = _normalize(left)
    right_normalized = _normalize(right)

    return (
        _mentions_cancel_paid_order(left_normalized)
        and _mentions_cancel_paid_order(right_normalized)
        and _permission_polarity(left_normalized)
        != _permission_polarity(right_normalized)
    )


def _mentions_cancel_paid_order(text: str) -> bool:
    return (
        any(term in text for term in {"cancelar", "cancelamento"})
        and any(term in text for term in {"pedido", "pedidos"})
        and any(term in text for term in {"pago", "pagos", "pagamento"})
    )


def _permission_polarity(text: str) -> str:
    deny_terms = {"nao deve permitir", "não deve permitir", "proibir"}
    if any(term in text for term in deny_terms):
        return "deny"
    if any(term in text for term in {"deve permitir", "deve poder", "pode cancelar"}):
        return "allow"
    return "unknown"


def _build_existing_conflict(
    requirement: Requirement,
    existing_requirement: ExistingRequirement,
) -> ConflictFinding:
    return ConflictFinding(
        requirement_id=requirement.id,
        conflicting_requirement_id=existing_requirement.id,
        explanation=(
            "O novo requisito permite cancelamento de pedido pago, enquanto a "
            "base existente registra restricao para cancelamento apos pagamento."
        ),
        severity=FindingSeverity.HIGH,
        evidence=[
            Evidence(
                source=requirement.source.source_path,
                excerpt=requirement.source.excerpt,
                explanation="Trecho do requisito novo analisado.",
            ),
            Evidence(
                source=existing_requirement.source_path,
                excerpt=existing_requirement.description,
                explanation="Requisito existente usado como base de comparacao.",
            ),
        ],
        confidence=0.9,
    )


def _build_batch_conflict(
    requirement: Requirement,
    other_requirement: Requirement,
) -> ConflictFinding:
    return ConflictFinding(
        requirement_id=requirement.id,
        conflicting_requirement_id=other_requirement.id,
        explanation="Os requisitos do mesmo lote definem permissoes opostas.",
        severity=FindingSeverity.HIGH,
        evidence=[
            Evidence(
                source=requirement.source.source_path,
                excerpt=requirement.source.excerpt,
                explanation="Primeiro requisito do lote.",
            ),
            Evidence(
                source=other_requirement.source.source_path,
                excerpt=other_requirement.source.excerpt,
                explanation="Segundo requisito do lote.",
            ),
        ],
        confidence=0.85,
    )


def _normalize(text: str) -> str:
    lowered = text.lower()
    replacements = {
        "á": "a",
        "à": "a",
        "ã": "a",
        "â": "a",
        "é": "e",
        "ê": "e",
        "í": "i",
        "ó": "o",
        "õ": "o",
        "ô": "o",
        "ú": "u",
        "ç": "c",
    }
    for original, replacement in replacements.items():
        lowered = lowered.replace(original, replacement)
    return lowered


def _requirements_prompt(requirements: list[Requirement]) -> str:
    return "\n".join(
        f"- {item.id} ({item.type.value}): {item.description}"
        for item in requirements
    )


def _existing_requirements_prompt(requirements: list[ExistingRequirement]) -> str:
    if not requirements:
        return "- Nenhuma base externa informada."
    return "\n".join(
        f"- {item.id}: {item.description}"
        for item in requirements
    )


def _is_valid_llm_conflict(item, valid_ids: set[str]) -> bool:
    if item.requirement_id not in valid_ids:
        return False
    if item.conflicting_requirement_id not in valid_ids:
        return False
    if item.requirement_id == item.conflicting_requirement_id:
        return False
    return True


def _parse_llm_payload(response, schema_type):
    return parse_structured_response(response, schema_type, "Conflict Analyst")
