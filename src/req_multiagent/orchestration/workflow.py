"""End-to-end requirements workflow orchestration."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from req_multiagent.analysis.ambiguity_agent import (
    detect_ambiguities,
    detect_ambiguities_with_llm,
)
from req_multiagent.analysis.conflict_agent import (
    detect_conflicts,
    detect_conflicts_with_llm,
)
from req_multiagent.analysis.prioritization_agent import (
    prioritize_requirements,
    prioritize_requirements_with_llm,
)
from req_multiagent.config import load_settings
from req_multiagent.ingestion.extractor_agent import (
    extract_requirements_from_text,
    extract_requirements_with_llm,
)
from req_multiagent.models import ConsolidatedReport
from req_multiagent.orchestration.consolidator_agent import (
    consolidate_report,
    consolidate_report_with_llm,
    render_report_markdown,
)
from req_multiagent.persistence.repository import RequirementsRepository


@dataclass
class WorkflowRunResult:
    """Result returned by the end-to-end workflow."""

    success: bool
    report: ConsolidatedReport | None = None
    report_markdown: str = ""
    error: str | None = None


def run_requirements_workflow(
    transcript_path: Path | str,
    database_path: Path | str | None = None,
    persist: bool = True,
    use_llm: bool | None = None,
) -> WorkflowRunResult:
    """Run extraction, analysis, prioritization, consolidation, and persistence."""

    path = Path(transcript_path)
    if not path.exists():
        return WorkflowRunResult(
            success=False,
            error=f"Transcript file not found: {path.as_posix()}",
        )
    if not path.is_file():
        return WorkflowRunResult(
            success=False,
            error=f"Transcript path is not a file: {path.as_posix()}",
        )

    try:
        transcript_text = path.read_text(encoding="utf-8")
        requirements = _extract_requirements(
            transcript_text=transcript_text,
            source_name=path.as_posix(),
            id_prefix=path.stem.upper().replace("-", "_"),
            use_llm=use_llm,
        )
        return _run_analysis_pipeline(
            transcript_name=path.name,
            requirements=requirements,
            database_path=database_path,
            persist=persist,
            use_llm=use_llm,
        )
    except OSError as exc:
        return WorkflowRunResult(
            success=False,
            error=f"Could not read or write workflow files: {exc}",
        )
    except Exception as exc:  # pragma: no cover - defensive workflow boundary
        return WorkflowRunResult(
            success=False,
            error=f"Workflow failed: {exc}",
        )


def run_requirements_workflow_from_text(
    transcript_text: str,
    source_name: str = "conversa_colada.md",
    database_path: Path | str | None = None,
    persist: bool = True,
    use_llm: bool | None = None,
) -> WorkflowRunResult:
    """Run the workflow from pasted or uploaded transcript text."""

    if not transcript_text.strip():
        return WorkflowRunResult(
            success=False,
            error="Transcript text is empty.",
        )

    try:
        source_path = Path(source_name)
        id_prefix = _build_id_prefix(source_path.stem)
        requirements = _extract_requirements(
            transcript_text=transcript_text,
            source_name=source_name,
            id_prefix=id_prefix,
            use_llm=use_llm,
        )
        return _run_analysis_pipeline(
            transcript_name=source_path.name,
            requirements=requirements,
            database_path=database_path,
            persist=persist,
            use_llm=use_llm,
        )
    except Exception as exc:  # pragma: no cover - defensive workflow boundary
        return WorkflowRunResult(
            success=False,
            error=f"Workflow failed: {exc}",
        )


def _extract_requirements(
    transcript_text: str,
    source_name: str,
    id_prefix: str,
    use_llm: bool | None,
):
    settings = load_settings()
    should_use_llm = settings.use_llm_agents if use_llm is None else use_llm
    if should_use_llm:
        return extract_requirements_with_llm(
            transcript=transcript_text,
            source_path=source_name,
            id_prefix=id_prefix,
        )
    return extract_requirements_from_text(
        transcript=transcript_text,
        source_path=source_name,
        id_prefix=id_prefix,
    )


def _run_analysis_pipeline(
    transcript_name: str,
    requirements,
    database_path: Path | str | None,
    persist: bool,
    use_llm: bool | None,
) -> WorkflowRunResult:
    settings = load_settings()
    should_use_llm = settings.use_llm_agents if use_llm is None else use_llm

    if should_use_llm:
        with ThreadPoolExecutor(max_workers=2) as executor:
            ambiguities_future = executor.submit(
                detect_ambiguities_with_llm,
                requirements,
            )
            conflicts_future = executor.submit(
                detect_conflicts_with_llm,
                requirements,
            )
            ambiguities = ambiguities_future.result()
            conflicts = conflicts_future.result()
        priorities = prioritize_requirements_with_llm(
            requirements,
            conflicts=conflicts,
        )
        report = consolidate_report_with_llm(
            transcript_name=transcript_name,
            requirements=requirements,
            ambiguities=ambiguities,
            conflicts=conflicts,
            priorities=priorities,
        )
    else:
        ambiguities = detect_ambiguities(requirements)
        conflicts = detect_conflicts(requirements)
        priorities = prioritize_requirements(requirements, conflicts=conflicts)
        report = consolidate_report(
            transcript_name=transcript_name,
            requirements=requirements,
            ambiguities=ambiguities,
            conflicts=conflicts,
            priorities=priorities,
        )
    report_markdown = render_report_markdown(report)

    if persist:
        repository = RequirementsRepository(database_path=database_path)
        repository.save_report(report)

    return WorkflowRunResult(
        success=True,
        report=report,
        report_markdown=report_markdown,
    )


def _build_id_prefix(source_stem: str) -> str:
    cleaned = "".join(
        character.upper() if character.isalnum() else "_"
        for character in source_stem
    ).strip("_")
    return cleaned or "CONVERSA"
