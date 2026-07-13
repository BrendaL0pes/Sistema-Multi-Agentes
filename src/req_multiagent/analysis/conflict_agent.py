"""Conflict detection agent and deterministic comparison helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from req_multiagent.config import load_settings
from req_multiagent.models import ConflictFinding, Evidence, FindingSeverity, Requirement

DEFAULT_EXISTING_REQUIREMENTS_PATH = Path(
    "data/existing_requirements/existing_requirements.md"
)

EXISTING_REQUIREMENT_PATTERN = re.compile(
    r"^##\s+(REQ-EXIST-\d+):\s*(.+)$",
    re.MULTILINE,
)
DESCRIPTION_PATTERN = re.compile(
    r"Descrição:\s*(.+)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ExistingRequirement:
    """Requirement loaded from the existing baseline."""

    id: str
    title: str
    description: str
    source_path: str


@dataclass(frozen=True)
class ConflictRule:
    """Rule that links a new requirement pattern to an existing baseline item."""

    existing_id: str
    required_terms: tuple[str, ...]
    explanation: str


CONFLICT_RULES = (
    ConflictRule(
        existing_id="REQ-EXIST-001",
        required_terms=("cancelar", "pedido pago"),
        explanation=(
            "O novo requisito permite cancelamento de pedido pago, mas a base "
            "existente proibe cancelamento apos a confirmacao do pagamento."
        ),
    ),
    ConflictRule(
        existing_id="REQ-EXIST-002",
        required_terms=("sugerir", "resposta"),
        explanation=(
            "O novo requisito sugere resposta automatica, mas a base existente "
            "exige revisao humana antes de qualquer envio ao cliente."
        ),
    ),
)

PROHIBITION_PATTERNS = (
    "nao deve permitir",
    "nao deve",
    "nao pode",
    "deve ser proibido",
)
PERMISSION_PATTERNS = (
    "deve poder",
    "deve permitir",
    "deve sugerir",
)


def create_conflict_agent():
    """Create the Agno agent responsible for conflict analysis.

    The import is intentionally lazy so tests that exercise deterministic
    comparison do not require installed model-provider packages or API keys.
    """

    from agno.agent import Agent
    from agno.models.groq import Groq

    settings = load_settings()
    return Agent(
        name="Conflict Analyst",
        role="Compare new requirements against existing baselines and batches.",
        model=Groq(id=settings.model_id),
        instructions=[
            "Responda em portugues.",
            "Compare requisitos novos com requisitos existentes e com o lote atual.",
            "Identifique contradicoes objetivas entre comportamentos esperados.",
            "Retorne os IDs conflitantes com justificativa objetiva.",
            "Nao invente conflitos quando os requisitos forem compativeis.",
        ],
        markdown=True,
    )


def load_existing_requirements(
    path: Path | str | None = None,
) -> list[ExistingRequirement]:
    """Load the existing requirement baseline from markdown."""

    requirements_path = Path(path) if path else DEFAULT_EXISTING_REQUIREMENTS_PATH
    content = requirements_path.read_text(encoding="utf-8")
    requirements: list[ExistingRequirement] = []

    for match in EXISTING_REQUIREMENT_PATTERN.finditer(content):
        section_start = match.end()
        next_heading = content.find("\n## ", section_start)
        section = (
            content[section_start:next_heading]
            if next_heading != -1
            else content[section_start:]
        )
        description_match = DESCRIPTION_PATTERN.search(section)
        if not description_match:
            continue

        requirements.append(
            ExistingRequirement(
                id=match.group(1),
                title=match.group(2).strip(),
                description=description_match.group(1).strip(),
                source_path=requirements_path.as_posix(),
            )
        )

    return requirements


def detect_conflicts(
    requirements: list[Requirement],
    existing_requirements_path: Path | str | None = None,
) -> list[ConflictFinding]:
    """Detect conflicts between new requirements, the baseline and the batch."""

    existing_requirements = load_existing_requirements(existing_requirements_path)
    existing_by_id = {item.id: item for item in existing_requirements}
    findings: list[ConflictFinding] = []
    seen_pairs: set[tuple[str, str]] = set()

    for requirement in requirements:
        findings.extend(
            _detect_existing_conflicts(
                requirement=requirement,
                existing_by_id=existing_by_id,
                seen_pairs=seen_pairs,
            )
        )

    findings.extend(_detect_batch_conflicts(requirements=requirements, seen_pairs=seen_pairs))
    return findings


def _detect_existing_conflicts(
    requirement: Requirement,
    existing_by_id: dict[str, ExistingRequirement],
    seen_pairs: set[tuple[str, str]],
) -> list[ConflictFinding]:
    findings: list[ConflictFinding] = []

    for rule in CONFLICT_RULES:
        if not _contains_all_terms(requirement.description, rule.required_terms):
            continue

        existing_requirement = existing_by_id.get(rule.existing_id)
        if existing_requirement is None:
            continue

        pair = _normalize_pair(requirement.id, existing_requirement.id)
        if pair in seen_pairs:
            continue

        seen_pairs.add(pair)
        findings.append(
            ConflictFinding(
                requirement_id=requirement.id,
                conflicting_requirement_id=existing_requirement.id,
                explanation=rule.explanation,
                severity=FindingSeverity.HIGH,
                evidence=[
                    Evidence(
                        source=requirement.source.source_path,
                        excerpt=requirement.description,
                        explanation="Requisito novo extraido da transcricao.",
                    ),
                    Evidence(
                        source=existing_requirement.source_path,
                        excerpt=existing_requirement.description,
                        explanation="Requisito existente usado como base de comparacao.",
                    ),
                ],
            )
        )

    return findings


def _detect_batch_conflicts(
    requirements: list[Requirement],
    seen_pairs: set[tuple[str, str]],
) -> list[ConflictFinding]:
    findings: list[ConflictFinding] = []

    for left_index, left_requirement in enumerate(requirements):
        for right_requirement in requirements[left_index + 1 :]:
            if not _requirements_conflict(
                left_requirement.description,
                right_requirement.description,
            ):
                continue

            pair = _normalize_pair(left_requirement.id, right_requirement.id)
            if pair in seen_pairs:
                continue

            seen_pairs.add(pair)
            findings.append(
                ConflictFinding(
                    requirement_id=left_requirement.id,
                    conflicting_requirement_id=right_requirement.id,
                    explanation=(
                        "Dois requisitos do lote atual descrevem comportamentos "
                        "contraditorios sobre o mesmo tema."
                    ),
                    severity=FindingSeverity.HIGH,
                    evidence=[
                        Evidence(
                            source=left_requirement.source.source_path,
                            excerpt=left_requirement.description,
                            explanation="Primeiro requisito conflitante do lote.",
                        ),
                        Evidence(
                            source=right_requirement.source.source_path,
                            excerpt=right_requirement.description,
                            explanation="Segundo requisito conflitante do lote.",
                        ),
                    ],
                )
            )

    return findings


def _requirements_conflict(left_text: str, right_text: str) -> bool:
    """Detect contradictory permission and prohibition statements."""

    shared_terms = _shared_topic_terms(left_text, right_text)
    if not shared_terms:
        return False

    left_polarity = _polarity(left_text)
    right_polarity = _polarity(right_text)
    return left_polarity != right_polarity and "neutral" not in {left_polarity, right_polarity}


def _shared_topic_terms(left_text: str, right_text: str) -> set[str]:
    left_tokens = set(_tokenize(left_text))
    right_tokens = set(_tokenize(right_text))
    topic_tokens = {
        "cancelar",
        "cancelamento",
        "pedido",
        "pago",
        "pagamento",
        "resposta",
        "sugerir",
        "envio",
        "aprovacao",
        "decisao",
    }
    return (left_tokens & right_tokens) & topic_tokens


def _polarity(text: str) -> str:
    normalized = _normalize_text(text)
    if any(pattern in normalized for pattern in PROHIBITION_PATTERNS):
        return "prohibition"
    if any(pattern in normalized for pattern in PERMISSION_PATTERNS):
        return "permission"
    return "neutral"


def _contains_all_terms(text: str, required_terms: tuple[str, ...]) -> bool:
    normalized = _normalize_text(text)
    return all(term in normalized for term in required_terms)


def _normalize_pair(left_id: str, right_id: str) -> tuple[str, str]:
    return tuple(sorted((left_id, right_id)))


def _normalize_text(text: str) -> str:
    normalized = text.lower()
    normalized = normalized.replace("ã", "a").replace("á", "a").replace("é", "e")
    normalized = normalized.replace("í", "i").replace("ó", "o").replace("ú", "u")
    normalized = normalized.replace("ç", "c")
    return normalized


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[\wÀ-ÿ]+", _normalize_text(text))
