from pathlib import Path

from req_multiagent.ingestion.extractor_agent import extract_requirements_from_file
from req_multiagent.models import RequirementType


def test_extractor_returns_structured_traceable_requirements() -> None:
    transcript_path = Path("data/synthetic_transcripts/transcript_01_checkout.md")

    requirements = extract_requirements_from_file(transcript_path)

    assert len(requirements) == 4
    assert requirements[0].id == "TRANSCRIPT_01_CHECKOUT-001"
    assert requirements[0].type == RequirementType.FUNCTIONAL
    assert requirements[0].source.source_path == transcript_path.as_posix()
    assert requirements[0].source.excerpt.startswith("- [RF]")
    assert requirements[0].source.start_line is not None


def test_extractor_classifies_non_functional_requirements() -> None:
    transcript_path = Path("data/synthetic_transcripts/transcript_01_checkout.md")

    requirements = extract_requirements_from_file(transcript_path)

    non_functional = [
        requirement
        for requirement in requirements
        if requirement.type == RequirementType.NON_FUNCTIONAL
    ]
    assert len(non_functional) == 1
    assert "rápida" in non_functional[0].description
