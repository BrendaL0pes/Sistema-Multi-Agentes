from req_multiagent.analysis.conflict_agent import detect_conflicts
from req_multiagent.ingestion.extractor_agent import extract_requirements_from_file


def test_detects_conflict_with_existing_requirement() -> None:
    requirements = extract_requirements_from_file(
        "data/synthetic_transcripts/transcript_01_checkout.md"
    )

    findings = detect_conflicts(requirements)

    assert len(findings) == 1
    assert findings[0].requirement_id == "TRANSCRIPT_01_CHECKOUT-003"
    assert findings[0].conflicting_requirement_id == "REQ-EXIST-001"
    assert "cancelamento" in findings[0].explanation.lower()
    assert findings[0].evidence


def test_returns_no_conflict_when_batch_has_no_contradiction() -> None:
    requirements = extract_requirements_from_file(
        "data/synthetic_transcripts/transcript_02_support.md"
    )

    findings = detect_conflicts(requirements)

    assert findings == []
