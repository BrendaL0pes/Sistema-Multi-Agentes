"""Ambiguity detection agent and deterministic analysis helpers."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from req_multiagent.config import load_settings
from req_multiagent.models import AmbiguityFinding, Evidence, FindingSeverity, Requirement

DEFAULT_WEAK_WORDS_PATH = Path("docs/corpus/weak_words_ptbr.json")


@dataclass(frozen=True)
class WeakWord:
    """A vague term used to flag ambiguous requirements."""

    term: str
    reason: str
    clarification_question: str


def create_ambiguity_agent():
    """Create the Agno agent responsible for ambiguity analysis.

    The import is intentionally lazy so tests that exercise deterministic
    detection do not require installed model-provider packages or API keys.
    """

    from agno.agent import Agent
    from agno.models.groq import Groq

    settings = load_settings()
    return Agent(
        name="Ambiguity Analyst",
        role="Detect vague terms in requirements and suggest clarifications.",
        model=Groq(id=settings.model_id),
        instructions=[
            "Responda em portugues.",
            "Identifique termos vagos em requisitos de software.",
            "Cruze os achados com criterios de qualidade e termos fracos do corpus.",
            "Gere perguntas objetivas de clarificacao para cada ambiguidade.",
            "Nao invente ambiguidades quando o requisito ja for verificavel.",
        ],
        markdown=True,
    )


def load_weak_words(path: Path | str | None = None) -> list[WeakWord]:
    """Load the weak-word dictionary used for ambiguity detection."""

    weak_words_path = Path(path) if path else DEFAULT_WEAK_WORDS_PATH
    payload = json.loads(weak_words_path.read_text(encoding="utf-8"))
    return [
        WeakWord(
            term=item["term"],
            reason=item["reason"],
            clarification_question=item["clarification_question"],
        )
        for item in payload["weak_words"]
    ]


def detect_ambiguities(
    requirements: list[Requirement],
    weak_words_path: Path | str | None = None,
) -> list[AmbiguityFinding]:
    """Detect ambiguous terms in requirements using the weak-word dictionary."""

    weak_words = load_weak_words(weak_words_path)
    findings: list[AmbiguityFinding] = []

    for requirement in requirements:
        for weak_word in weak_words:
            if not _term_matches(requirement.description, weak_word.term):
                continue

            findings.append(
                AmbiguityFinding(
                    requirement_id=requirement.id,
                    term=weak_word.term,
                    explanation=weak_word.reason,
                    clarification_questions=[weak_word.clarification_question],
                    severity=FindingSeverity.MEDIUM,
                    evidence=[
                        Evidence(
                            source=DEFAULT_WEAK_WORDS_PATH.as_posix(),
                            excerpt=weak_word.term,
                            explanation=weak_word.reason,
                        )
                    ],
                )
            )

    return findings


def _term_matches(text: str, term: str) -> bool:
    """Match a weak term against requirement text, tolerating simple inflections."""

    normalized_text = text.lower()
    normalized_term = term.lower()

    if normalized_term in normalized_text:
        return True

    text_tokens = re.findall(r"[\wÀ-ÿ]+", normalized_text)
    term_stem = normalized_term[: max(len(normalized_term) - 1, 4)]
    return any(token.startswith(term_stem) for token in text_tokens)
