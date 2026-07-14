"""Gap detection agent and deterministic completeness helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from req_multiagent.analysis.conflict_agent import (
    DEFAULT_EXISTING_REQUIREMENTS_PATH,
    load_existing_requirements,
)
from req_multiagent.config import load_settings
from req_multiagent.models import Evidence, FindingSeverity, GapFinding, Requirement

REQUIREMENT_MARKER_PATTERN = re.compile(
    r"^\s*(?:[-*]\s*)?\[(RF|RNF|FUNCIONAL|NAO-FUNCIONAL|NÃO-FUNCIONAL)\]",
    re.IGNORECASE,
)

GAP_NARRATIVE_SIGNALS = (
    "ainda precisamos definir",
    "nao ficou claro",
    "precisamos definir",
)


@dataclass(frozen=True)
class IncompletenessRule:
    """Rule that flags missing details against an existing baseline requirement."""

    baseline_id: str
    new_signals: tuple[str, ...]
    required_concepts: tuple[str, ...]
    explanation: str
    clarification_question: str


INCOMPLETENESS_RULES = (
    IncompletenessRule(
        baseline_id="REQ-EXIST-003",
        new_signals=("registrar", "decisao"),
        required_concepts=("usuario", "data", "hora", "justificativa"),
        explanation=(
            "O requisito menciona registro de decisao, mas nao explicita usuario, "
            "data, hora e justificativa exigidos pela base existente."
        ),
        clarification_question=(
            "Quais campos obrigatorios devem compor o registro da decisao de aprovacao?"
        ),
    ),
)


def create_gap_agent():
    """Create the Agno agent responsible for gap analysis.

    The import is intentionally lazy so tests that exercise deterministic
    detection do not require installed model-provider packages or API keys.
    """

    from agno.agent import Agent
    from agno.models.groq import Groq

    settings = load_settings()
    return Agent(
        name="Gap Analyst",
        role="Detect missing rules, unanswered questions and incomplete requirements.",
        model=Groq(id=settings.model_id),
        instructions=[
            "Responda em portugues.",
            "Identifique lacunas em transcricoes e requisitos incompletos.",
            "Compare novos requisitos com a base existente quando houver criterio de completude.",
            "Gere perguntas objetivas para fechar cada lacuna identificada.",
            "Nao invente lacunas quando o requisito ja estiver completo.",
        ],
        markdown=True,
    )


def detect_gaps(
    requirements: list[Requirement],
    transcript_path: Path | str | None = None,
    transcript_text: str | None = None,
    existing_requirements_path: Path | str | None = None,
) -> list[GapFinding]:
    """Detect narrative and completeness gaps in requirements and transcripts."""

    findings: list[GapFinding] = []
    if transcript_text is not None:
        source = (
            Path(transcript_path).as_posix()
            if transcript_path is not None
            else "transcricao_inline"
        )
        findings.extend(_detect_narrative_gaps_from_text(transcript_text, source))
    elif transcript_path is not None:
        path = Path(transcript_path)
        findings.extend(
            _detect_narrative_gaps_from_text(
                path.read_text(encoding="utf-8"),
                path.as_posix(),
            )
        )

    findings.extend(
        _detect_incompleteness_gaps(
            requirements=requirements,
            existing_requirements_path=existing_requirements_path,
        )
    )
    return findings


def _detect_narrative_gaps_from_text(
    transcript_text: str,
    source_path: str,
) -> list[GapFinding]:
    findings: list[GapFinding] = []

    for line_number, line in enumerate(transcript_text.splitlines(), start=1):
        if not line.strip() or line.startswith("#") or REQUIREMENT_MARKER_PATTERN.match(line):
            continue

        normalized = _normalize_text(line)
        matched_signal = next(
            (signal for signal in GAP_NARRATIVE_SIGNALS if signal in normalized),
            None,
        )
        if matched_signal is None:
            continue

        findings.append(
            GapFinding(
                requirement_id=None,
                topic=_build_topic(line),
                explanation=(
                    "A transcricao registra uma regra ou decisao ainda nao definida "
                    "formalmente em um requisito estruturado."
                ),
                clarification_questions=[_build_clarification_question(line)],
                severity=FindingSeverity.MEDIUM,
                evidence=[
                    Evidence(
                        source=source_path,
                        excerpt=line.strip(),
                        explanation=(
                            f"Trecho narrativo com sinal de lacuna: '{matched_signal}'."
                        ),
                    )
                ],
            )
        )

    return findings


def _detect_incompleteness_gaps(
    requirements: list[Requirement],
    existing_requirements_path: Path | str | None = None,
) -> list[GapFinding]:
    existing_by_id = {
        item.id: item
        for item in load_existing_requirements(existing_requirements_path)
    }
    findings: list[GapFinding] = []

    for requirement in requirements:
        normalized_description = _normalize_text(requirement.description)
        for rule in INCOMPLETENESS_RULES:
            if not _contains_all_terms(normalized_description, rule.new_signals):
                continue

            missing_concepts = [
                concept
                for concept in rule.required_concepts
                if concept not in normalized_description
            ]
            if not missing_concepts:
                continue

            baseline = existing_by_id.get(rule.baseline_id)
            findings.append(
                GapFinding(
                    requirement_id=requirement.id,
                    topic="completude de registro",
                    explanation=rule.explanation,
                    clarification_questions=[rule.clarification_question],
                    severity=FindingSeverity.MEDIUM,
                    evidence=[
                        Evidence(
                            source=requirement.source.source_path,
                            excerpt=requirement.description,
                            explanation="Requisito novo considerado incompleto.",
                        ),
                        Evidence(
                            source=(
                                baseline.source_path
                                if baseline
                                else DEFAULT_EXISTING_REQUIREMENTS_PATH.as_posix()
                            ),
                            excerpt=(
                                baseline.description
                                if baseline
                                else rule.baseline_id
                            ),
                            explanation="Base existente usada como referencia de completude.",
                        ),
                    ],
                )
            )

    return findings


def _build_topic(line: str) -> str:
    cleaned = line.split(":", 1)[-1].strip()
    words = cleaned.rstrip(".").split()
    return " ".join(words[:6])


def _build_clarification_question(line: str) -> str:
    topic = _build_topic(line)
    return f"Qual regra formal deve ser definida para: {topic}?"


def _contains_all_terms(text: str, required_terms: tuple[str, ...]) -> bool:
    return all(term in text for term in required_terms)


def _normalize_text(text: str) -> str:
    normalized = text.lower()
    normalized = normalized.replace("ã", "a").replace("á", "a").replace("é", "e")
    normalized = normalized.replace("í", "i").replace("ó", "o").replace("ú", "u")
    normalized = normalized.replace("ç", "c")
    return normalized
