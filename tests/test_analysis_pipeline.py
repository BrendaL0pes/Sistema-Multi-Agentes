from dataclasses import dataclass
from pathlib import Path

import pytest

from req_multiagent.analysis.ambiguity_agent import (
    DEFAULT_ISO_CRITERIA_PATH,
    detect_ambiguities,
)
from req_multiagent.analysis.conflict_agent import detect_conflicts
from req_multiagent.analysis.gap_agent import detect_gaps
from req_multiagent.analysis.prioritization_agent import prioritize_requirements
from req_multiagent.ingestion.extractor_agent import extract_requirements_from_file
from req_multiagent.models import MoscowPriority


@pytest.fixture
def knowledge_base_path(tmp_path: Path) -> Path:
    """Provide an isolated knowledge-base directory for each test."""

    return tmp_path / "knowledge_base"


@dataclass
class AnalysisResult:
    """Bundle of analysis outputs for a single transcript."""

    requirements: list
    ambiguities: list
    conflicts: list
    gaps: list
    priorities: list


def _run_analysis_pipeline(
    transcript_path: Path,
    knowledge_base_path: Path,
) -> AnalysisResult:
    requirements = extract_requirements_from_file(transcript_path)
    ambiguities = detect_ambiguities(
        requirements=requirements,
        index_path=knowledge_base_path,
        corpus_path=DEFAULT_ISO_CRITERIA_PATH,
    )
    conflicts = detect_conflicts(requirements=requirements)
    gaps = detect_gaps(
        requirements=requirements,
        transcript_path=transcript_path,
    )
    priorities = prioritize_requirements(
        requirements=requirements,
        ambiguities=ambiguities,
        conflicts=conflicts,
    )
    return AnalysisResult(
        requirements=requirements,
        ambiguities=ambiguities,
        conflicts=conflicts,
        gaps=gaps,
        priorities=priorities,
    )


def test_analysis_pipeline_for_checkout_transcript(
    knowledge_base_path: Path,
) -> None:
    transcript_path = Path("data/synthetic_transcripts/transcript_01_checkout.md")

    result = _run_analysis_pipeline(transcript_path, knowledge_base_path)

    assert len(result.requirements) == 4
    assert len(result.ambiguities) == 1
    assert len(result.conflicts) == 1
    assert result.gaps == []
    assert len(result.priorities) == 4
    assert any(item.priority == MoscowPriority.WONT for item in result.priorities)


def test_analysis_pipeline_for_support_transcript(
    knowledge_base_path: Path,
) -> None:
    transcript_path = Path("data/synthetic_transcripts/transcript_02_support.md")

    result = _run_analysis_pipeline(transcript_path, knowledge_base_path)

    assert len(result.ambiguities) == 1
    assert len(result.conflicts) == 1
    assert len(result.gaps) == 1
    assert result.gaps[0].requirement_id is None


def test_analysis_pipeline_for_approvals_transcript(
    knowledge_base_path: Path,
) -> None:
    transcript_path = Path("data/synthetic_transcripts/transcript_03_approvals.md")

    result = _run_analysis_pipeline(transcript_path, knowledge_base_path)

    assert len(result.ambiguities) == 1
    assert result.conflicts == []
    assert len(result.gaps) == 2
    assert any(item.priority == MoscowPriority.MUST for item in result.priorities)
