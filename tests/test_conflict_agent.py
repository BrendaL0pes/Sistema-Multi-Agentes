from pathlib import Path

from req_multiagent.analysis.conflict_agent import (
    DEFAULT_EXISTING_REQUIREMENTS_PATH,
    detect_conflicts,
    load_existing_requirements,
)
from req_multiagent.ingestion.extractor_agent import extract_requirements_from_file


def _detect_from_transcript(transcript_path: Path) -> list:
    requirements = extract_requirements_from_file(transcript_path)
    return detect_conflicts(requirements=requirements)


def test_load_existing_requirements_parses_baseline() -> None:
    existing_requirements = load_existing_requirements()

    assert len(existing_requirements) == 3
    assert existing_requirements[0].id == "REQ-EXIST-001"
    assert "cancelamento" in existing_requirements[0].description.lower()
    assert existing_requirements[0].source_path == (
        DEFAULT_EXISTING_REQUIREMENTS_PATH.as_posix()
    )


def test_detects_cancelamento_conflict_in_checkout_transcript() -> None:
    transcript_path = Path("data/synthetic_transcripts/transcript_01_checkout.md")

    findings = _detect_from_transcript(transcript_path)

    assert len(findings) == 1
    assert findings[0].requirement_id == "TRANSCRIPT_01_CHECKOUT-003"
    assert findings[0].conflicting_requirement_id == "REQ-EXIST-001"
    assert "cancelamento" in findings[0].explanation.lower()
    assert len(findings[0].evidence) == 2


def test_detects_auto_response_conflict_in_support_transcript() -> None:
    transcript_path = Path("data/synthetic_transcripts/transcript_02_support.md")

    findings = _detect_from_transcript(transcript_path)

    assert len(findings) == 1
    assert findings[0].requirement_id == "TRANSCRIPT_02_SUPPORT-002"
    assert findings[0].conflicting_requirement_id == "REQ-EXIST-002"
    assert "revisao humana" in findings[0].explanation.lower()


def test_skips_false_positive_in_approvals_transcript() -> None:
    transcript_path = Path("data/synthetic_transcripts/transcript_03_approvals.md")

    findings = _detect_from_transcript(transcript_path)

    assert findings == []
