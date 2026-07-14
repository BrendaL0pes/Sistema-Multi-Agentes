"""Requirement extraction agent and deterministic parsing helpers."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Literal

from req_multiagent.config import load_settings
from req_multiagent.llm_utils import run_structured_agent
from req_multiagent.models import Requirement, RequirementType, SourceTrace

REQUIREMENT_PATTERN = re.compile(
    r"^\s*(?:[-*]\s*)?\[(RF|RNF|FUNCIONAL|NAO-FUNCIONAL|NÃO-FUNCIONAL)\]\s*(.+)$",
    re.IGNORECASE,
)

INLINE_REQUIREMENT_PATTERN = re.compile(
    r"\[(RF|RNF|FUNCIONAL|NAO-FUNCIONAL|NÃO-FUNCIONAL)\]\s*(.+)$",
    re.IGNORECASE,
)


NATURAL_REQUIREMENT_CUES = (
    "precisa",
    "precisamos",
    "deve",
    "devem",
    "deveria",
    "deveriam",
    "tem que",
    "obrigatorio",
    "obrigatoria",
    "obrigatoriamente",
    "nao pode",
    "impedir",
    "bloquear",
    "registrar",
    "guardar",
    "avisado",
    "notificacao",
    "seria bom",
    "apenas usuarios",
    "so gestor pode",
)

NON_FUNCTIONAL_CUES = (
    "rapido",
    "rapidamente",
    "desempenho",
    "performance",
    "tempo",
    "segundos",
    "minutos",
    "disponibilidade",
    "seguranca",
    "eficiente",
    "confiavel",
)

SPEAKER_PREFIX_PATTERN = re.compile(r"^\s*[^:\n]{1,40}:\s*")


class LlmExtractionUnavailable(RuntimeError):
    """Raised when LLM extraction is requested but cannot run."""


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
        model=Groq(
            id=settings.model_id,
            api_key=settings.groq_api_key,
            timeout=60,
            max_retries=2,
            retries=2,
        ),
        instructions=[
            "Responda em portugues.",
            "Extraia requisitos funcionais e nao funcionais de transcricoes.",
            "Preserve rastreabilidade citando o trecho de origem.",
            "Classifique cada requisito como functional ou non_functional.",
            "Retorne uma lista estruturada, objetiva e sem inventar requisitos.",
        ],
        markdown=True,
    )


def extract_requirements_with_llm(
    transcript: str,
    source_path: str,
    id_prefix: str = "REQ",
) -> list[Requirement]:
    """Extract requirements from natural language using the configured Agno LLM."""

    settings = load_settings()
    if not settings.groq_api_key:
        raise LlmExtractionUnavailable(
            "GROQ_API_KEY nao configurada. Preencha o .env para usar a LLM."
        )

    from pydantic import BaseModel, Field

    class ExtractedRequirement(BaseModel):
        description: str = Field(
            description="Descricao objetiva do requisito em portugues."
        )
        type: Literal["functional", "non_functional"] = Field(
            description="Tipo do requisito."
        )
        source_excerpt: str = Field(
            description=(
                "Trecho exato ou muito proximo da conversa que originou "
                "o requisito."
            )
        )

    class ExtractedRequirements(BaseModel):
        requirements: list[ExtractedRequirement]

    prompt = (
        "Extraia requisitos candidatos da conversa abaixo. "
        "Nao invente requisitos. Use functional para comportamento do sistema "
        "e non_functional para qualidade, desempenho, seguranca, usabilidade "
        "ou restricoes mensuraveis.\n\n"
        f"Conversa:\n{transcript}"
    )
    payload = run_structured_agent(
        create_extractor_agent(),
        prompt,
        ExtractedRequirements,
        "Requirements Extractor",
    )

    requirements: list[Requirement] = []
    for item in payload.requirements:
        description = item.description.strip()
        if not description:
            continue
        requirement_id = f"{id_prefix}-{len(requirements) + 1:03d}"
        line_number = _find_excerpt_line(transcript, item.source_excerpt)
        requirements.append(
            Requirement(
                id=requirement_id,
                title=_build_title(description),
                description=description,
                type=RequirementType(item.type),
                source=SourceTrace(
                    source_path=source_path,
                    excerpt=item.source_excerpt.strip() or description,
                    start_line=line_number,
                    end_line=line_number,
                ),
                metadata={"extraction_mode": "llm_agno"},
            )
        )

    return requirements


def extract_requirements_from_text(
    transcript: str,
    source_path: str,
    id_prefix: str = "REQ",
) -> list[Requirement]:
    """Extract requirements from marked or natural stakeholder transcripts."""

    requirements: list[Requirement] = []
    transcript_lines = transcript.splitlines()
    has_explicit_markers = any(
        _match_explicit_requirement(line) for line in transcript_lines
    )

    for line_number, line in enumerate(transcript_lines, start=1):
        match = _match_explicit_requirement(line)
        if match:
            raw_type, raw_text = match.groups()
            requirement_type = _parse_requirement_type(raw_type)
            description = raw_text.strip()
            extraction_mode = "marker"
        else:
            if has_explicit_markers:
                continue
            natural_requirement = _extract_natural_requirement(line)
            if natural_requirement is None:
                continue
            description, requirement_type = natural_requirement
            extraction_mode = "natural_language_heuristic"

        requirement_id = f"{id_prefix}-{len(requirements) + 1:03d}"
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
                metadata={"extraction_mode": extraction_mode},
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


def _match_explicit_requirement(line: str):
    return REQUIREMENT_PATTERN.search(line) or INLINE_REQUIREMENT_PATTERN.search(line)


def _parse_requirement_type(raw_type: str) -> RequirementType:
    normalized = raw_type.upper().replace("Ã", "A")
    if normalized in {"RNF", "NAO-FUNCIONAL", "NÃO-FUNCIONAL"}:
        return RequirementType.NON_FUNCTIONAL
    return RequirementType.FUNCTIONAL


def _build_title(description: str) -> str:
    words = description.rstrip(".").split()
    return " ".join(words[:8])


def _extract_natural_requirement(line: str) -> tuple[str, RequirementType] | None:
    cleaned_line = line.strip()
    if not cleaned_line:
        return None

    statement = SPEAKER_PREFIX_PATTERN.sub("", cleaned_line).strip()
    if not statement or statement.endswith("?"):
        return None

    normalized = _normalize(statement)
    if not any(cue in normalized for cue in _normalized_cues(NATURAL_REQUIREMENT_CUES)):
        return None

    requirement_type = (
        RequirementType.NON_FUNCTIONAL
        if any(cue in normalized for cue in _normalized_cues(NON_FUNCTIONAL_CUES))
        else RequirementType.FUNCTIONAL
    )
    return _normalize_requirement_sentence(statement), requirement_type


def _normalize_requirement_sentence(statement: str) -> str:
    cleaned = statement.strip().rstrip(".")
    return f"{cleaned}."


def _find_excerpt_line(transcript: str, excerpt: str) -> int | None:
    normalized_excerpt = _normalize(excerpt)
    if not normalized_excerpt:
        return None

    for line_number, line in enumerate(transcript.splitlines(), start=1):
        normalized_line = _normalize(line)
        if (
            normalized_excerpt in normalized_line
            or normalized_line in normalized_excerpt
        ):
            return line_number
    return None


def _normalized_cues(cues: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(_normalize(cue) for cue in cues)


def _normalize(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text)
    without_accents = "".join(
        character for character in ascii_text if not unicodedata.combining(character)
    )
    return without_accents.casefold()
