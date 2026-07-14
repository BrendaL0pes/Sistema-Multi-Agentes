from pathlib import Path
import shutil

from req_multiagent.analysis.ambiguity_agent import (
    DEFAULT_ISO_CRITERIA_PATH,
    DEFAULT_WEAK_WORDS_PATH,
    detect_ambiguities,
    load_weak_words,
)
from req_multiagent.ingestion.extractor_agent import extract_requirements_from_file
from req_multiagent.models import RequirementType


TEST_KNOWLEDGE_BASE_PATH = Path("storage/test_ambiguity_agent")


def setup_function() -> None:
    if TEST_KNOWLEDGE_BASE_PATH.exists():
        shutil.rmtree(TEST_KNOWLEDGE_BASE_PATH)


def teardown_function() -> None:
    if TEST_KNOWLEDGE_BASE_PATH.exists():
        shutil.rmtree(TEST_KNOWLEDGE_BASE_PATH)


def _detect_from_transcript(
    transcript_path: Path,
) -> list:
    requirements = extract_requirements_from_file(transcript_path)
    return detect_ambiguities(
        requirements=requirements,
        index_path=TEST_KNOWLEDGE_BASE_PATH,
        corpus_path=DEFAULT_ISO_CRITERIA_PATH,
    )


def test_detects_rapida_ambiguity_in_checkout_transcript() -> None:
    transcript_path = Path("data/synthetic_transcripts/transcript_01_checkout.md")

    findings = _detect_from_transcript(transcript_path)

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


def test_detects_simples_ambiguity_in_support_transcript() -> None:
    transcript_path = Path("data/synthetic_transcripts/transcript_02_support.md")

    findings = _detect_from_transcript(transcript_path)

    assert len(findings) == 1
    assert findings[0].term == "simples"
    assert findings[0].requirement_id == "TRANSCRIPT_02_SUPPORT-003"
    assert "simplificado" in findings[0].clarification_questions[0].lower()


def test_detects_eficiente_ambiguity_in_approvals_transcript() -> None:
    transcript_path = Path("data/synthetic_transcripts/transcript_03_approvals.md")

    findings = _detect_from_transcript(transcript_path)

    assert len(findings) == 1
    assert findings[0].term == "eficiente"
    assert findings[0].requirement_id == "TRANSCRIPT_03_APPROVALS-003"
    assert "métrica" in findings[0].clarification_questions[0].lower()


def test_skips_functional_requirements_without_weak_words() -> None:
    transcript_path = Path("data/synthetic_transcripts/transcript_01_checkout.md")
    requirements = extract_requirements_from_file(transcript_path)
    functional_requirements = [
        requirement
        for requirement in requirements
        if requirement.type == RequirementType.FUNCTIONAL
    ]

    findings = detect_ambiguities(
        requirements=functional_requirements,
        index_path=TEST_KNOWLEDGE_BASE_PATH,
        corpus_path=DEFAULT_ISO_CRITERIA_PATH,
    )

    assert findings == []


def test_load_weak_words_returns_catalog() -> None:
    weak_words = load_weak_words()

    assert len(weak_words) == 6
    assert weak_words[0].term
    assert weak_words[0].clarification_question
