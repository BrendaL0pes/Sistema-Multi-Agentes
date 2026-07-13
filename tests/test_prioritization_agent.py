from pathlib import Path

import pytest

from req_multiagent.analysis.ambiguity_agent import (
    DEFAULT_ISO_CRITERIA_PATH,
    detect_ambiguities,
)
from req_multiagent.analysis.conflict_agent import detect_conflicts
from req_multiagent.analysis.prioritization_agent import prioritize_requirements
from req_multiagent.ingestion.extractor_agent import extract_requirements_from_file
from req_multiagent.models import MoscowPriority


@pytest.fixture
def knowledge_base_path(tmp_path: Path) -> Path:
    """Provide an isolated knowledge-base directory for each test."""

    return tmp_path / "knowledge_base"


def _prioritize_from_transcript(
    transcript_path: Path,
    knowledge_base_path: Path,
) -> list:
    requirements = extract_requirements_from_file(transcript_path)
    ambiguities = detect_ambiguities(
        requirements=requirements,
        index_path=knowledge_base_path,
        corpus_path=DEFAULT_ISO_CRITERIA_PATH,
    )
    conflicts = detect_conflicts(requirements=requirements)
    return prioritize_requirements(
        requirements=requirements,
        ambiguities=ambiguities,
        conflicts=conflicts,
    )


def _priority_by_id(assessments: list, requirement_suffix: str) -> MoscowPriority:
    assessment = next(
        item
        for item in assessments
        if item.requirement_id.endswith(requirement_suffix)
    )
    return assessment.priority


def test_prioritizes_checkout_requirements_from_planted_findings(
    knowledge_base_path: Path,
) -> None:
    transcript_path = Path("data/synthetic_transcripts/transcript_01_checkout.md")

    assessments = _prioritize_from_transcript(transcript_path, knowledge_base_path)

    assert len(assessments) == 4
    assert _priority_by_id(assessments, "001") == MoscowPriority.MUST
    assert _priority_by_id(assessments, "002") == MoscowPriority.COULD
    assert _priority_by_id(assessments, "003") == MoscowPriority.WONT
    assert _priority_by_id(assessments, "004") == MoscowPriority.SHOULD


def test_prioritizes_support_requirements_from_planted_findings(
    knowledge_base_path: Path,
) -> None:
    transcript_path = Path("data/synthetic_transcripts/transcript_02_support.md")

    assessments = _prioritize_from_transcript(transcript_path, knowledge_base_path)

    assert _priority_by_id(assessments, "002") == MoscowPriority.WONT
    assert _priority_by_id(assessments, "003") == MoscowPriority.COULD
    assert _priority_by_id(assessments, "004") == MoscowPriority.SHOULD


def test_prioritizes_approvals_critical_flow_as_must(
    knowledge_base_path: Path,
) -> None:
    transcript_path = Path("data/synthetic_transcripts/transcript_03_approvals.md")

    assessments = _prioritize_from_transcript(transcript_path, knowledge_base_path)

    assert _priority_by_id(assessments, "001") == MoscowPriority.MUST
    assert _priority_by_id(assessments, "002") == MoscowPriority.MUST
    assert _priority_by_id(assessments, "003") == MoscowPriority.COULD
    assert _priority_by_id(assessments, "004") == MoscowPriority.SHOULD
