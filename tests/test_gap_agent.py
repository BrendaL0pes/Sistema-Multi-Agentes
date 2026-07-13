from pathlib import Path

from req_multiagent.analysis.gap_agent import detect_gaps
from req_multiagent.ingestion.extractor_agent import extract_requirements_from_file


def _detect_from_transcript(transcript_path: Path) -> list:
    requirements = extract_requirements_from_file(transcript_path)
    return detect_gaps(
        requirements=requirements,
        transcript_path=transcript_path,
    )


def test_detects_manager_absence_gap_in_approvals_transcript() -> None:
    transcript_path = Path("data/synthetic_transcripts/transcript_03_approvals.md")

    findings = _detect_from_transcript(transcript_path)
    narrative_gaps = [finding for finding in findings if finding.requirement_id is None]

    assert len(narrative_gaps) == 1
    assert "definir" in narrative_gaps[0].topic.lower()
    assert "gestor" in narrative_gaps[0].evidence[0].excerpt.lower()


def test_detects_incomplete_decision_record_in_approvals_transcript() -> None:
    transcript_path = Path("data/synthetic_transcripts/transcript_03_approvals.md")

    findings = _detect_from_transcript(transcript_path)
    completeness_gaps = [
        finding for finding in findings if finding.requirement_id is not None
    ]

    assert len(completeness_gaps) == 1
    assert completeness_gaps[0].requirement_id == "TRANSCRIPT_03_APPROVALS-004"
    assert "usuario" in completeness_gaps[0].explanation.lower()
    assert "REQ-EXIST-003" in completeness_gaps[0].evidence[1].excerpt or (
        "justificativa" in completeness_gaps[0].evidence[1].excerpt.lower()
    )


def test_detects_unclear_auto_response_gap_in_support_transcript() -> None:
    transcript_path = Path("data/synthetic_transcripts/transcript_02_support.md")

    findings = _detect_from_transcript(transcript_path)
    narrative_gaps = [finding for finding in findings if finding.requirement_id is None]

    assert len(narrative_gaps) == 1
    assert "revis" in narrative_gaps[0].evidence[0].excerpt.lower()


def test_skips_gap_detection_in_checkout_transcript() -> None:
    transcript_path = Path("data/synthetic_transcripts/transcript_01_checkout.md")

    findings = _detect_from_transcript(transcript_path)

    assert findings == []
