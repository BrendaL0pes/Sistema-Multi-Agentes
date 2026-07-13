from pathlib import Path

import pytest

from req_multiagent.analysis.ambiguity_agent import (
    DEFAULT_ISO_CRITERIA_PATH,
    DEFAULT_WEAK_WORDS_PATH,
    detect_ambiguities,
)
from req_multiagent.ingestion.extractor_agent import extract_requirements_from_file
from req_multiagent.models import RequirementType


@pytest.fixture
def knowledge_base_path(tmp_path: Path) -> Path:
    """Provide an isolated knowledge-base directory for each test."""

    return tmp_path / "knowledge_base"


def _detect_from_transcript(
    transcript_path: Path,
    knowledge_base_path: Path,
) -> list:
    requirements = extract_requirements_from_file(transcript_path)
    return detect_ambiguities(
        requirements=requirements,
        index_path=knowledge_base_path,
        corpus_path=DEFAULT_ISO_CRITERIA_PATH,
    )


def test_detects_rapida_ambiguity_in_checkout_transcript(
    knowledge_base_path: Path,
) -> None:
    transcript_path = Path("data/synthetic_transcripts/transcript_01_checkout.md")

    findings = _detect_from_transcript(transcript_path, knowledge_base_path)

    assert len(findings) == 1
    assert findings[0].term == "rápido"
    assert findings[0].requirement_id == "TRANSCRIPT_01_CHECKOUT-002"
    assert findings[0].clarification_questions
    assert any(
        source == DEFAULT_WEAK_WORDS_PATH.as_posix()
        for source in {item.source for item in findings[0].evidence}
    )
    assert any(
        DEFAULT_ISO_CRITERIA_PATH.as_posix() in item.source
        for item in findings[0].evidence
    )


def test_detects_simples_ambiguity_in_support_transcript(
    knowledge_base_path: Path,
) -> None:
    transcript_path = Path("data/synthetic_transcripts/transcript_02_support.md")

    findings = _detect_from_transcript(transcript_path, knowledge_base_path)

    assert len(findings) == 1
    assert findings[0].term == "simples"
    assert findings[0].requirement_id == "TRANSCRIPT_02_SUPPORT-003"
    assert "simplificado" in findings[0].clarification_questions[0].lower()


def test_detects_eficiente_ambiguity_in_approvals_transcript(
    knowledge_base_path: Path,
) -> None:
    transcript_path = Path("data/synthetic_transcripts/transcript_03_approvals.md")

    findings = _detect_from_transcript(transcript_path, knowledge_base_path)

    assert len(findings) == 1
    assert findings[0].term == "eficiente"
    assert findings[0].requirement_id == "TRANSCRIPT_03_APPROVALS-003"
    assert "métrica" in findings[0].clarification_questions[0].lower()


def test_skips_functional_requirements_without_weak_words(
    knowledge_base_path: Path,
) -> None:
    transcript_path = Path("data/synthetic_transcripts/transcript_01_checkout.md")
    requirements = extract_requirements_from_file(transcript_path)
    functional_requirements = [
        requirement
        for requirement in requirements
        if requirement.type == RequirementType.FUNCTIONAL
    ]

    findings = detect_ambiguities(
        requirements=functional_requirements,
        index_path=knowledge_base_path,
        corpus_path=DEFAULT_ISO_CRITERIA_PATH,
    )

    assert findings == []
