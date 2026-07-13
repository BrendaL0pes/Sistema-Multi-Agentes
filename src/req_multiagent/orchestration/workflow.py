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
from req_multiagent.orchestration.project_update_agent import (
    adjust_requirements_from_instruction,
    answer_project_question,
    merge_incremental_conversation,
)
from req_multiagent.persistence.repository import RequirementsRepository


@dataclass
class WorkflowRunResult:
    """Result returned by the end-to-end workflow."""

    success: bool
    report: ConsolidatedReport | None = None
    report_markdown: str = ""
    error: str | None = None
    message: str = ""


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


def increment_requirements_project(
    report: ConsolidatedReport,
    transcript_text: str,
    source_name: str,
    database_path: Path | str | None = None,
    persist: bool = True,
    use_llm: bool | None = None,
) -> WorkflowRunResult:
    """Increment an existing project with a new stakeholder conversation."""

    if not transcript_text.strip():
        return WorkflowRunResult(success=False, error="Transcript text is empty.")

    try:
        next_prefix = _project_prefix(report.requirements, source_name)
        candidate_requirements = _extract_requirements(
            transcript_text=transcript_text,
            source_name=source_name,
            id_prefix=next_prefix,
            use_llm=use_llm,
        )
        merged_requirements, message = merge_incremental_conversation(
            current_requirements=report.requirements,
            new_requirements=candidate_requirements,
            transcript_text=transcript_text,
            source_name=source_name,
        )
        result = analyze_requirements_project(
            project_name=_report_project_name(report),
            requirements=merged_requirements,
            database_path=database_path,
            persist=persist,
            use_llm=use_llm,
            existing_report=report,
        )
        result.message = message
        if result.report:
            result.report.chat_messages = report.chat_messages
        return result
    except Exception as exc:  # pragma: no cover - defensive workflow boundary
        return WorkflowRunResult(
            success=False,
            error=f"Workflow failed: {exc}",
        )


def adjust_requirements_project(
    report: ConsolidatedReport,
    instruction: str,
    database_path: Path | str | None = None,
    persist: bool = True,
    use_llm: bool | None = None,
) -> WorkflowRunResult:
    """Adjust project requirements based on a user instruction."""

    if not instruction.strip():
        return WorkflowRunResult(
            success=False,
            error="Adjustment instruction is empty.",
        )

    try:
        adjusted_requirements, message = adjust_requirements_from_instruction(
            current_requirements=report.requirements,
            instruction=instruction,
        )
        result = analyze_requirements_project(
            project_name=_report_project_name(report),
            requirements=adjusted_requirements,
            database_path=database_path,
            persist=persist,
            use_llm=use_llm,
            existing_report=report,
        )
        result.message = message
        if result.report:
            result.report.chat_messages = report.chat_messages
        return result
    except Exception as exc:  # pragma: no cover - defensive workflow boundary
        return WorkflowRunResult(
            success=False,
            error=f"Workflow failed: {exc}",
        )


def analyze_requirements_project(
    project_name: str,
    requirements,
    database_path: Path | str | None = None,
    persist: bool = True,
    use_llm: bool | None = None,
    existing_report: ConsolidatedReport | None = None,
) -> WorkflowRunResult:
    """Re-run project analysis from an existing requirement set."""

    result = _run_analysis_pipeline(
        transcript_name=project_name,
        requirements=requirements,
        database_path=database_path,
        persist=False,
        use_llm=use_llm,
    )
    if not result.success or result.report is None:
        return result

    if existing_report is not None:
        result.report.id = existing_report.id
        result.report.title = existing_report.title
        result.report.created_at = existing_report.created_at
        result.report.chat_messages = existing_report.chat_messages
        result.report_markdown = render_report_markdown(result.report)

    if persist:
        repository = RequirementsRepository(database_path=database_path)
        repository.save_report(result.report)

    return result


def answer_requirements_project_question(
    report: ConsolidatedReport,
    question: str,
) -> WorkflowRunResult:
    """Answer a chat question without changing the project artifacts."""

    if not question.strip():
        return WorkflowRunResult(success=False, error="Question is empty.")

    try:
        message = answer_project_question(report=report, question=question)
        return WorkflowRunResult(
            success=True,
            report=report,
            report_markdown=render_report_markdown(report),
            message=message,
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
        conflicts = detect_conflicts(requirements, compare_existing=False)
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


def _project_prefix(requirements, source_name: str) -> str:
    if requirements:
        first_id = requirements[0].id
        if "-" in first_id:
            return first_id.rsplit("-", maxsplit=1)[0]
    return _build_id_prefix(Path(source_name).stem)


def _report_project_name(report: ConsolidatedReport) -> str:
    return report.title.replace("Relatorio de requisitos - ", "")
