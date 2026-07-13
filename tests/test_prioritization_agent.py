from req_multiagent.analysis.conflict_agent import detect_conflicts
from req_multiagent.analysis.prioritization_agent import prioritize_requirements
from req_multiagent.ingestion.extractor_agent import extract_requirements_from_file
from req_multiagent.models import MoscowPriority, RequirementType


def test_prioritizes_functional_and_non_functional_requirements() -> None:
    requirements = extract_requirements_from_file(
        "data/synthetic_transcripts/transcript_02_support.md"
    )

    assessments = prioritize_requirements(requirements)
    by_id = {assessment.requirement_id: assessment for assessment in assessments}

    assert by_id["TRANSCRIPT_02_SUPPORT-001"].priority == MoscowPriority.MUST
    assert by_id["TRANSCRIPT_02_SUPPORT-003"].priority == MoscowPriority.SHOULD
    assert any(
        requirement.type == RequirementType.NON_FUNCTIONAL
        for requirement in requirements
    )


def test_conflicted_requirement_waits_for_human_decision() -> None:
    requirements = extract_requirements_from_file(
        "data/synthetic_transcripts/transcript_01_checkout.md"
    )
    conflicts = detect_conflicts(requirements)

    assessments = prioritize_requirements(requirements, conflicts=conflicts)
    by_id = {assessment.requirement_id: assessment for assessment in assessments}

    conflicted = by_id["TRANSCRIPT_01_CHECKOUT-003"]
    assert conflicted.priority == MoscowPriority.WONT
    assert conflicted.limitations
