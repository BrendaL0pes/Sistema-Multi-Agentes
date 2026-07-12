"""Shared domain models for the requirements pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class RequirementType(str, Enum):
    """Supported requirement categories."""

    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"


class FindingSeverity(str, Enum):
    """Severity levels for analysis findings."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MoscowPriority(str, Enum):
    """MoSCoW priority categories."""

    MUST = "must"
    SHOULD = "should"
    COULD = "could"
    WONT = "wont"


@dataclass(frozen=True)
class SourceTrace:
    """Reference to the source text that originated a requirement or finding."""

    source_path: str
    excerpt: str
    start_line: int | None = None
    end_line: int | None = None


@dataclass(frozen=True)
class Evidence:
    """Evidence used to justify an agent output."""

    source: str
    excerpt: str
    explanation: str


@dataclass
class Requirement:
    """Requirement extracted from stakeholder input."""

    id: str
    title: str
    description: str
    type: RequirementType
    source: SourceTrace
    acceptance_criteria: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AmbiguityFinding:
    """Ambiguity detected in a requirement."""

    requirement_id: str
    term: str
    explanation: str
    clarification_questions: list[str]
    severity: FindingSeverity = FindingSeverity.MEDIUM
    evidence: list[Evidence] = field(default_factory=list)
    confidence: float | None = None
    limitations: list[str] = field(default_factory=list)


@dataclass
class ConflictFinding:
    """Conflict between two requirements."""

    requirement_id: str
    conflicting_requirement_id: str
    explanation: str
    severity: FindingSeverity = FindingSeverity.HIGH
    evidence: list[Evidence] = field(default_factory=list)
    confidence: float | None = None
    limitations: list[str] = field(default_factory=list)


@dataclass
class PriorityAssessment:
    """MoSCoW priority assigned to a requirement."""

    requirement_id: str
    priority: MoscowPriority
    rationale: str
    evidence: list[Evidence] = field(default_factory=list)
    confidence: float | None = None
    limitations: list[str] = field(default_factory=list)


@dataclass
class ConsolidatedReport:
    """Final traceable report produced by the requirements workflow."""

    id: str
    title: str
    requirements: list[Requirement]
    ambiguities: list[AmbiguityFinding] = field(default_factory=list)
    conflicts: list[ConflictFinding] = field(default_factory=list)
    priorities: list[PriorityAssessment] = field(default_factory=list)
    summary: str = ""
    limitations: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
