"""
requirements_models.py
----------------------
Modelos de dominio compartidos para Gestión de Requisitos (SDLAS).

Este archivo define EXCLUSIVAMENTE estructuras de datos (dataclasses y enums)
reutilizables por:
- RequirementsAgent
- Validadores y analizadores
- Auditoría / Control Interno
- Handoff a Diseño y Desarrollo
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

# ------------------------------------------------------------------
# Helper serialization mixin
# ------------------------------------------------------------------


class SerializableDataclass:
    """Mixin para serializar objetos de dominio a diccionario."""

    def to_dict(self) -> dict[str, Any]:
        def convert(value: Any) -> Any:
            if isinstance(value, Enum):
                return value.value
            if isinstance(value, datetime):
                return value.isoformat()
            if isinstance(value, list):
                return [convert(v) for v in value]
            if isinstance(value, dict):
                return {k: convert(v) for k, v in value.items()}
            return value

        return {k: convert(v) for k, v in asdict(self).items()}  # type: ignore[call-overload]

    @classmethod
    def _parse_enum(cls, enum_cls: type[Enum], value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, enum_cls):
            return value
        normalized = str(value).strip().lower()
        for member in enum_cls:
            if member.value == normalized:
                return member
        raise ValueError(f"Valor inválido para {enum_cls.__name__}: {value}")


# ------------------------------------------------------------------
# Enums (catálogos controlados / auditables)
# ------------------------------------------------------------------


class RequirementType(Enum):
    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"
    CONSTRAINT = "constraint"
    SECURITY = "security"
    PERFORMANCE = "performance"
    INTERFACE = "interface"


class RequirementStatus(Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"
    ANALYZED = "analyzed"


class PriorityLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    MUST = "must"
    SHOULD = "should"
    COULD = "could"
    WONT = "wont"


class ComplexityLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_CHANGES = "needs_changes"
    CHANGES_REQUESTED = "changes_requested"
    TIMED_OUT = "timed_out"


# ------------------------------------------------------------------
# Core Requirement Models
# ------------------------------------------------------------------


@dataclass
class Requirement(SerializableDataclass):
    id: str
    title: str
    description: str
    type: RequirementType
    priority: PriorityLevel
    source: str
    acceptance_criteria: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    status: RequirementStatus = RequirementStatus.PENDING
    ambiguity_score: float = 0.0
    complexity_level: ComplexityLevel = ComplexityLevel.MEDIUM
    tags: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    priority_score: float = 0.0
    ambiguity_report: AmbiguityReport | None = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @property
    def req_type(self) -> RequirementType:
        return self.type

    @property
    def is_complete(self) -> bool:
        return bool(self.title and self.description and len(self.acceptance_criteria) >= 2)

    @property
    def is_ambiguous(self) -> bool:
        return self.ambiguity_score > 0.0 or bool(
            self.ambiguity_report and self.ambiguity_report.flags
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Requirement:
        type_value = data.get("type") or data.get("req_type") or "functional"
        priority_value = data.get("priority", "medium")
        return cls(
            id=str(data.get("id", f"REQ-{uuid.uuid4().hex[:8].upper()}")),
            title=str(data.get("title", "")),
            description=str(data.get("description", "")),
            type=cls._parse_enum(RequirementType, type_value),
            priority=cls._parse_enum(PriorityLevel, priority_value),
            source=str(data.get("source", "user")),
            acceptance_criteria=list(data.get("acceptance_criteria", []) or []),
            dependencies=list(data.get("dependencies", []) or []),
            status=cls._parse_enum(RequirementStatus, data.get("status", "pending")),
            ambiguity_score=float(data.get("ambiguity_score", 0.0) or 0.0),
            complexity_level=cls._parse_enum(
                ComplexityLevel, data.get("complexity_level", "medium")
            ),
            tags=list(data.get("tags", []) or []),
            risks=list(data.get("risks", []) or []),
            priority_score=float(data.get("priority_score", 0.0) or 0.0),
            created_at=datetime.fromisoformat(data["created_at"])
            if data.get("created_at")
            else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"])
            if data.get("updated_at")
            else datetime.now(),
        )


@dataclass
class RequirementChange(SerializableDataclass):
    """Registro de cambios a un requisito (audit trail)."""

    change_id: str
    requirement_id: str
    changed_by: str
    change_reason: str
    previous_state: dict[str, Any]
    new_state: dict[str, Any]
    change_date: datetime = field(default_factory=datetime.now)


# ------------------------------------------------------------------
# Use Cases & SRS Versioning
# ------------------------------------------------------------------


@dataclass
class UseCase(SerializableDataclass):
    id: str
    name: str
    actor: str
    description: str
    related_requirements: list[str] = field(default_factory=list)
    preconditions: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)
    postconditions: list[str] = field(default_factory=list)
    alternative_flows: list[dict[str, Any]] = field(default_factory=list)
    exception_flows: list[dict[str, Any]] = field(default_factory=list)
    priority: PriorityLevel = PriorityLevel.MEDIUM


@dataclass
class SRSVersion(SerializableDataclass):
    """Versionado formal del SRS."""

    version: str
    created_by: str
    created_at: datetime = field(default_factory=datetime.now)
    change_log: list[str] = field(default_factory=list)


@dataclass
class SoftwareRequirementsSpec(SerializableDataclass):
    id: str
    project_name: str
    description: str = ""
    version: str = "1.0.0"
    current_version: SRSVersion = field(
        default_factory=lambda: SRSVersion(version="1.0.0", created_by="requirements_agent")
    )
    requirements: list[Requirement] = field(default_factory=list)
    use_cases: list[UseCase] = field(default_factory=list)
    glossary: dict[str, str] = field(default_factory=dict)
    assumptions: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    approved_by: str | None = None
    approved_at: datetime | None = None
    completeness_score: float = 0.0
    ambiguity_score: float = 0.0
    version_history: list[dict[str, Any]] = field(default_factory=list)
    traceability: list[TraceabilityEntry] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


# ------------------------------------------------------------------
# Traceability (auditoría extremo a extremo)
# ------------------------------------------------------------------


@dataclass
class TraceabilityEntry(SerializableDataclass):
    source_id: str | None = None
    target_id: str | None = None
    link_type: str | None = None
    rationale: str | None = None
    status: str | None = None
    design_artifact: str | None = None
    development_artifact: str | None = None
    test_artifact: str | None = None


@dataclass
class TraceabilityMatrix(SerializableDataclass):
    srs_id: str
    entries: list[TraceabilityEntry] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)

    def add_entry(self, entry: TraceabilityEntry) -> None:
        self.entries.append(entry)


# ------------------------------------------------------------------
# Approval Flow
# ------------------------------------------------------------------


@dataclass
class ApprovalRequest(SerializableDataclass):
    request_id: str
    srs_id: str
    srs_version: str | None = None
    summary: str | None = None
    completeness_score: float = 0.0
    ambiguity_score: float = 0.0
    total_requirements: int = 0
    issues: list[str] = field(default_factory=list)
    requested_by: str = "requirements_agent"
    timeout_seconds: int = 0
    requested_at: datetime = field(default_factory=datetime.now)
    comments: str | None = None

    @property
    def id(self) -> str:
        return self.request_id


@dataclass
class ApprovalResponse(SerializableDataclass):
    request_id: str
    status: ApprovalStatus
    reviewed_by: str
    reviewed_at: datetime = field(default_factory=datetime.now)
    comments: str | None = None
    change_requests: list[str] = field(default_factory=list)

    @property
    def responded_at(self) -> datetime:
        return self.reviewed_at

    @property
    def reviewer(self) -> str:
        return self.reviewed_by


# ------------------------------------------------------------------
# Handoff & Quality Analysis
# ------------------------------------------------------------------


@dataclass
class DesignHandoffPackage(SerializableDataclass):
    id: str
    srs_id: str
    version: str
    requirements: list[Requirement]
    use_cases: list[UseCase]
    traceability_matrix: TraceabilityMatrix | None
    approval_response: ApprovalResponse | None = None
    design_guidelines: list[str] = field(default_factory=list)
    constraints_for_design: list[str] = field(default_factory=list)
    priority_order: list[str] = field(default_factory=list)
    notes: str | None = None
    created_at: datetime = field(default_factory=datetime.now)


class AmbiguityFlag(Enum):
    VAGUE_TERM = "vague_term"
    MISSING_METRIC = "missing_metric"
    UNCLEAR_ACTOR = "unclear_actor"
    MISSING_BOUNDARY = "missing_boundary"
    PASSIVE_VOICE = "passive_voice"
    MULTIPLE_INTERPRETATIONS = "multiple_interpretations"
    UNDEFINED_REFERENCE = "undefined_reference"

    def __str__(self) -> str:
        return self.value


@dataclass
class AmbiguityReport(SerializableDataclass):
    srs_id: str | None = None
    flags: list[AmbiguityFlag] = field(default_factory=list)
    details: list[str] = field(default_factory=list)
    score: float = 0.0
    suggestions: list[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)
