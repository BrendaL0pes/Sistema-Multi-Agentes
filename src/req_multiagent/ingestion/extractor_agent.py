"""Requirement extraction agent and deterministic parsing helpers."""

from __future__ import annotations

import re
from pathlib import Path

from req_multiagent.config import load_settings
from req_multiagent.models import Requirement, RequirementType, SourceTrace

REQUIREMENT_PATTERN = re.compile(
    r"^\s*(?:[-*]\s*)?\[(RF|RNF|FUNCIONAL|NAO-FUNCIONAL|NÃO-FUNCIONAL)\]\s*(.+)$",
    re.IGNORECASE,
)


def create_extractor_agent():
    """Create the Agno agent responsible for requirement extraction.

    The import is intentionally lazy so tests that exercise deterministic
    parsing do not require installed model-provider packages or API keys.
    """

    from agno.agent import Agent
    from agno.models.groq import Groq

    settings = load_settings()
    return Agent(
        name="Requirements Extractor",
        role="Extract structured requirements from stakeholder transcripts.",
        model=Groq(id=settings.model_id),
        instructions=[
            "Responda em portugues.",
            "Extraia requisitos funcionais e nao funcionais de transcricoes.",
            "Preserve rastreabilidade citando o trecho de origem.",
            "Classifique cada requisito como functional ou non_functional.",
            "Retorne uma lista estruturada, objetiva e sem inventar requisitos.",
        ],
        markdown=True,
    )


def extract_requirements_from_text(
    transcript: str,
    source_path: str,
    id_prefix: str = "REQ",
) -> list[Requirement]:
    """Extract requirements from a transcript using repository sample markers.

    The synthetic transcripts use explicit markers such as ``[RF]`` and
    ``[RNF]``. This keeps the extraction testable while the Agno agent remains
    available for model-assisted runs.
    """

    requirements: list[Requirement] = []
    for line_number, line in enumerate(transcript.splitlines(), start=1):
        match = REQUIREMENT_PATTERN.match(line)
        if not match:
            continue

        raw_type, raw_text = match.groups()
        requirement_type = _parse_requirement_type(raw_type)
        requirement_id = f"{id_prefix}-{len(requirements) + 1:03d}"
        description = raw_text.strip()
        requirements.append(
            Requirement(
                id=requirement_id,
                title=_build_title(description),
                description=description,
                type=requirement_type,
                source=SourceTrace(
                    source_path=source_path,
                    excerpt=line.strip(),
                    start_line=line_number,
                    end_line=line_number,
                ),
            )
        )

    return requirements


def extract_requirements_from_file(path: Path | str) -> list[Requirement]:
    """Read a transcript file and extract structured requirements from it."""

    transcript_path = Path(path)
    return extract_requirements_from_text(
        transcript=transcript_path.read_text(encoding="utf-8"),
        source_path=transcript_path.as_posix(),
        id_prefix=transcript_path.stem.upper().replace("-", "_"),
    )


def _parse_requirement_type(raw_type: str) -> RequirementType:
    normalized = raw_type.upper().replace("Ã", "A")
    if normalized in {"RNF", "NAO-FUNCIONAL", "NÃO-FUNCIONAL"}:
        return RequirementType.NON_FUNCTIONAL
    return RequirementType.FUNCTIONAL


def _build_title(description: str) -> str:
    words = description.rstrip(".").split()
    return " ".join(words[:8])
