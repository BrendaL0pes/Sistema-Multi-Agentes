"""SQLite repository for requirements workflow artifacts."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from req_multiagent.config import load_settings
from req_multiagent.models import (
    AmbiguityFinding,
    ConflictFinding,
    ConsolidatedReport,
    Evidence,
    FindingSeverity,
    GapFinding,
    MoscowPriority,
    PriorityAssessment,
    Requirement,
    RequirementType,
    SourceTrace,
)


class RepositoryError(RuntimeError):
    """Raised when workflow persistence fails."""


class RequirementsRepository:
    """SQLite-backed repository for generated requirements reports."""

    def __init__(self, database_path: Path | str | None = None) -> None:
        settings = load_settings()
        self.database_path = (
            Path(database_path) if database_path else settings.database_path
        )

    def initialize(self) -> None:
        """Create database tables when they do not exist."""

        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = self._connect()
        try:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS reports (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS requirements (
                    id TEXT PRIMARY KEY,
                    report_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    type TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    source_excerpt TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    FOREIGN KEY(report_id) REFERENCES reports(id)
                )
                """
            )
            connection.commit()
        finally:
            connection.close()

    def reset(self) -> None:
        """Remove local workflow state and recreate an empty database."""

        if self.database_path.exists():
            self.database_path.unlink()
        self.initialize()

    def save_report(self, report: ConsolidatedReport) -> None:
        """Persist a consolidated report and its requirements."""

        self.initialize()
        connection = self._connect()
        try:
            connection.execute(
                """
                INSERT OR REPLACE INTO reports
                (id, title, summary, payload, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    report.id,
                    report.title,
                    report.summary,
                    _to_json(report),
                    report.created_at.isoformat(),
                ),
            )
            connection.execute(
                "DELETE FROM requirements WHERE report_id = ?",
                (report.id,),
            )
            connection.executemany(
                """
                INSERT OR REPLACE INTO requirements
                (
                    id,
                    report_id,
                    title,
                    description,
                    type,
                    source_path,
                    source_excerpt,
                    payload
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        requirement.id,
                        report.id,
                        requirement.title,
                        requirement.description,
                        requirement.type.value,
                        requirement.source.source_path,
                        requirement.source.excerpt,
                        _to_json(requirement),
                    )
                    for requirement in report.requirements
                ],
            )
            connection.commit()
        except sqlite3.Error as exc:
            raise RepositoryError(f"Failed to persist workflow report: {exc}") from exc
        finally:
            connection.close()

    def list_requirements(self) -> list[dict[str, Any]]:
        """List persisted requirements with traceability fields."""

        self.initialize()
        connection = self._connect()
        try:
            rows = connection.execute(
                """
                SELECT
                    id,
                    report_id,
                    title,
                    description,
                    type,
                    source_path,
                    source_excerpt
                FROM requirements
                ORDER BY id
                """
            ).fetchall()
        finally:
            connection.close()

        return [dict(row) for row in rows]

    def list_reports(self) -> list[dict[str, Any]]:
        """List persisted consolidated reports."""

        self.initialize()
        connection = self._connect()
        try:
            rows = connection.execute(
                """
                SELECT id, title, summary, created_at
                FROM reports
                ORDER BY created_at DESC
                """
            ).fetchall()
        finally:
            connection.close()

        return [dict(row) for row in rows]

    def get_report(self, report_id: str) -> ConsolidatedReport | None:
        """Load a full persisted report by id."""

        self.initialize()
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT payload FROM reports WHERE id = ?",
                (report_id,),
            ).fetchone()
        finally:
            connection.close()

        if row is None:
            return None
        return _report_from_payload(json.loads(row["payload"]))

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection


def _to_json(value: Any) -> str:
    return json.dumps(_to_payload(value), ensure_ascii=False, indent=2)


def _to_payload(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value):
        return {key: _to_payload(item) for key, item in asdict(value).items()}
    if isinstance(value, list):
        return [_to_payload(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_payload(item) for key, item in value.items()}
    return value


def _report_from_payload(payload: dict[str, Any]) -> ConsolidatedReport:
    return ConsolidatedReport(
        id=payload["id"],
        title=payload["title"],
        requirements=[
            _requirement_from_payload(item)
            for item in payload.get("requirements", [])
        ],
        ambiguities=[
            _ambiguity_from_payload(item)
            for item in payload.get("ambiguities", [])
        ],
        conflicts=[
            _conflict_from_payload(item)
            for item in payload.get("conflicts", [])
        ],
        gaps=[
            _gap_from_payload(item)
            for item in payload.get("gaps", [])
        ],
        priorities=[
            _priority_from_payload(item)
            for item in payload.get("priorities", [])
        ],
        summary=payload.get("summary", ""),
        limitations=payload.get("limitations", []),
        created_at=datetime.fromisoformat(payload["created_at"]),
        chat_messages=payload.get("chat_messages", []),
    )


def _requirement_from_payload(payload: dict[str, Any]) -> Requirement:
    source = payload["source"]
    return Requirement(
        id=payload["id"],
        title=payload["title"],
        description=payload["description"],
        type=RequirementType(payload["type"]),
        source=SourceTrace(
            source_path=source["source_path"],
            excerpt=source["excerpt"],
            start_line=source.get("start_line"),
            end_line=source.get("end_line"),
        ),
        acceptance_criteria=payload.get("acceptance_criteria", []),
        tags=payload.get("tags", []),
        metadata=payload.get("metadata", {}),
    )


def _ambiguity_from_payload(payload: dict[str, Any]) -> AmbiguityFinding:
    return AmbiguityFinding(
        requirement_id=payload["requirement_id"],
        term=payload["term"],
        explanation=payload["explanation"],
        clarification_questions=payload.get("clarification_questions", []),
        severity=FindingSeverity(payload.get("severity", FindingSeverity.MEDIUM.value)),
        evidence=[_evidence_from_payload(item) for item in payload.get("evidence", [])],
        confidence=payload.get("confidence"),
        limitations=payload.get("limitations", []),
    )


def _conflict_from_payload(payload: dict[str, Any]) -> ConflictFinding:
    return ConflictFinding(
        requirement_id=payload["requirement_id"],
        conflicting_requirement_id=payload["conflicting_requirement_id"],
        explanation=payload["explanation"],
        severity=FindingSeverity(payload.get("severity", FindingSeverity.HIGH.value)),
        evidence=[_evidence_from_payload(item) for item in payload.get("evidence", [])],
        confidence=payload.get("confidence"),
        limitations=payload.get("limitations", []),
    )


def _gap_from_payload(payload: dict[str, Any]) -> GapFinding:
    return GapFinding(
        requirement_id=payload.get("requirement_id"),
        topic=payload["topic"],
        explanation=payload["explanation"],
        clarification_questions=payload.get("clarification_questions", []),
        severity=FindingSeverity(payload.get("severity", FindingSeverity.MEDIUM.value)),
        evidence=[_evidence_from_payload(item) for item in payload.get("evidence", [])],
        confidence=payload.get("confidence"),
        limitations=payload.get("limitations", []),
    )


def _priority_from_payload(payload: dict[str, Any]) -> PriorityAssessment:
    return PriorityAssessment(
        requirement_id=payload["requirement_id"],
        priority=MoscowPriority(payload["priority"]),
        rationale=payload["rationale"],
        evidence=[_evidence_from_payload(item) for item in payload.get("evidence", [])],
        confidence=payload.get("confidence"),
        limitations=payload.get("limitations", []),
    )


def _evidence_from_payload(payload: dict[str, Any]) -> Evidence:
    return Evidence(
        source=payload["source"],
        excerpt=payload["excerpt"],
        explanation=payload["explanation"],
    )
