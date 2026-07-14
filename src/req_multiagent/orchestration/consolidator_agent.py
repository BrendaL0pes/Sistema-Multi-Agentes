"""Consolidated report agent and deterministic report builder."""

from __future__ import annotations

from datetime import UTC, datetime

from req_multiagent.config import load_settings
from req_multiagent.llm_utils import run_structured_agent
from req_multiagent.models import (
    AmbiguityFinding,
    ConflictFinding,
    ConsolidatedReport,
    GapFinding,
    PriorityAssessment,
    Requirement,
)


def create_consolidator_agent():
    """Create the Agno agent responsible for final report synthesis."""

    from agno.agent import Agent
    from agno.models.groq import Groq

    settings = load_settings()
    return Agent(
        name="Requirements Consolidator",
        role="Create a traceable requirements report from analysis outputs.",
        model=Groq(
            id=settings.model_id,
            api_key=settings.groq_api_key,
            timeout=60,
            max_retries=2,
            retries=2,
        ),
        instructions=[
            "Responda em portugues.",
            "Consolide requisitos, ambiguidades, conflitos e prioridades.",
            "Preserve rastreabilidade ate a fonte de cada requisito.",
            "Destaque limitacoes e pontos que exigem revisao humana.",
        ],
        markdown=True,
    )


def consolidate_report(
    transcript_name: str,
    requirements: list[Requirement],
    ambiguities: list[AmbiguityFinding],
    conflicts: list[ConflictFinding],
    priorities: list[PriorityAssessment],
    gaps: list[GapFinding] | None = None,
) -> ConsolidatedReport:
    """Build a consolidated report from workflow outputs."""

    gap_findings = gaps or []
    created_at = datetime.now(UTC)
    timestamp = created_at.strftime("%Y%m%d%H%M%S%f")
    report_id = f"REPORT-{_slugify(transcript_name)}-{timestamp}"
    limitations = _collect_limitations(ambiguities, conflicts, priorities, gap_findings)
    summary = (
        f"Foram extraidos {len(requirements)} requisitos, com "
        f"{len(ambiguities)} ambiguidade(s), {len(conflicts)} conflito(s), "
        f"{len(gap_findings)} lacuna(s) e {len(priorities)} prioridade(s) MoSCoW."
    )

    return ConsolidatedReport(
        id=report_id,
        title=f"Relatorio de requisitos - {transcript_name}",
        requirements=requirements,
        ambiguities=ambiguities,
        conflicts=conflicts,
        gaps=gap_findings,
        priorities=priorities,
        summary=summary,
        limitations=limitations,
        created_at=created_at,
    )


def consolidate_report_with_llm(
    transcript_name: str,
    requirements: list[Requirement],
    ambiguities: list[AmbiguityFinding],
    conflicts: list[ConflictFinding],
    priorities: list[PriorityAssessment],
    gaps: list[GapFinding] | None = None,
) -> ConsolidatedReport:
    """Build a consolidated report with LLM-generated synthesis fields."""

    settings = load_settings()
    if not settings.groq_api_key:
        raise RuntimeError("GROQ_API_KEY nao configurada para usar a LLM.")

    from pydantic import BaseModel

    class LlmConsolidation(BaseModel):
        summary: str
        limitations: list[str]

    base_report = consolidate_report(
        transcript_name=transcript_name,
        requirements=requirements,
        ambiguities=ambiguities,
        conflicts=conflicts,
        gaps=gaps,
        priorities=priorities,
    )
    prompt = (
        "Consolide o resultado da analise de requisitos. Gere um resumo "
        "executivo objetivo e liste limitacoes ou pontos que exigem revisao "
        "humana. Nao altere IDs nem invente novos requisitos.\n\n"
        f"Requisitos: {len(requirements)}\n"
        f"Ambiguidades: {len(ambiguities)}\n"
        f"Conflitos: {len(conflicts)}\n"
        f"Lacunas: {len(gaps or [])}\n"
        f"Prioridades: {len(priorities)}\n\n"
        f"Detalhes:\n{render_report_markdown(base_report)}"
    )
    payload = run_structured_agent(
        create_consolidator_agent(),
        prompt,
        LlmConsolidation,
        "Requirements Consolidator",
    )
    base_report.summary = payload.summary
    base_report.limitations = sorted(
        set([*base_report.limitations, *payload.limitations])
    )
    return base_report


def render_report_markdown(report: ConsolidatedReport) -> str:
    """Render a consolidated report as Markdown for CLI and UI display."""

    lines = [
        f"# {report.title}",
        "",
        f"**ID:** {report.id}",
        f"**Criado em:** {report.created_at.isoformat()}",
        "",
        "## Resumo",
        "",
        report.summary,
        "",
        "## Requisitos Extraidos",
        "",
    ]

    for requirement in report.requirements:
        lines.extend(
            [
                f"### {requirement.id} - {requirement.title}",
                "",
                f"- **Tipo:** {requirement.type.value}",
                f"- **Descricao:** {requirement.description}",
                f"- **Fonte:** {requirement.source.source_path}",
                f"- **Trecho:** {requirement.source.excerpt}",
                "",
            ]
        )

    lines.extend(["## Ambiguidades", ""])
    if report.ambiguities:
        for finding in report.ambiguities:
            lines.extend(
                [
                    f"- **{finding.requirement_id}** usa `{finding.term}`: "
                    f"{finding.explanation}",
                    f"  - Pergunta: {finding.clarification_questions[0]}",
                ]
            )
    else:
        lines.append("- Nenhuma ambiguidade detectada.")

    lines.extend(["", "## Conflitos", ""])
    if report.conflicts:
        for finding in report.conflicts:
            lines.append(
                f"- **{finding.requirement_id}** conflita com "
                f"**{finding.conflicting_requirement_id}**: {finding.explanation}"
            )
    else:
        lines.append("- Nenhum conflito detectado.")

    lines.extend(["", "## Lacunas", ""])
    if report.gaps:
        for finding in report.gaps:
            label = (
                finding.requirement_id
                if finding.requirement_id
                else f"Narrativa ({finding.topic})"
            )
            lines.extend(
                [
                    f"- **{label}** — {finding.topic}: {finding.explanation}",
                ]
            )
            if finding.clarification_questions:
                lines.append(
                    f"  - Pergunta: {finding.clarification_questions[0]}"
                )
    else:
        lines.append("- Nenhuma lacuna detectada.")

    lines.extend(["", "## Priorizacao MoSCoW", ""])
    for assessment in report.priorities:
        lines.append(
            f"- **{assessment.requirement_id}:** {assessment.priority.value} - "
            f"{assessment.rationale}"
        )

    lines.extend(["", "## Limitacoes", ""])
    if report.limitations:
        for limitation in report.limitations:
            lines.append(f"- {limitation}")
    else:
        lines.append("- Nenhuma limitacao especifica registrada.")

    return "\n".join(lines).strip() + "\n"


def _collect_limitations(
    ambiguities: list[AmbiguityFinding],
    conflicts: list[ConflictFinding],
    priorities: list[PriorityAssessment],
    gaps: list[GapFinding] | None = None,
) -> list[str]:
    limitations: list[str] = []
    for item in [*ambiguities, *conflicts, *priorities, *(gaps or [])]:
        limitations.extend(item.limitations)

    if conflicts:
        limitations.append("Requisitos conflitantes exigem decisao humana.")
    if ambiguities:
        limitations.append("Termos ambiguos precisam de clarificacao com stakeholders.")
    if gaps:
        limitations.append("Lacunas identificadas exigem definicao formal com stakeholders.")

    return sorted(set(limitations))


def _slugify(value: str) -> str:
    return (
        value.upper()
        .replace(".MD", "")
        .replace(" ", "_")
        .replace("-", "_")
    )
