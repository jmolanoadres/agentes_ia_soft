
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

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional
from enum import Enum

# ------------------------------------------------------------------
# Enums (catálogos controlados / auditables)
# ------------------------------------------------------------------

class RequirementType(Enum):
    FUNCTIONAL = "functional"
    NON_FUNCTIONAL = "non_functional"
    CONSTRAINT = "constraint"


class RequirementStatus(Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"


class PriorityLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


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


# ------------------------------------------------------------------
# Core Requirement Models
# ------------------------------------------------------------------

@dataclass
class Requirement:
    id: str
    title: str
    description: str
    type: RequirementType
    priority: PriorityLevel
    source: str
    acceptance_criteria: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    status: RequirementStatus = RequirementStatus.PENDING
    ambiguity_score: float = 0.0
    complexity_level: ComplexityLevel = ComplexityLevel.MEDIUM
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class RequirementChange:
    """Registro de cambios a un requisito (audit trail)."""
    change_id: str
    requirement_id: str
    changed_by: str
    change_reason: str
    previous_state: Dict
    new_state: Dict
    change_date: datetime = field(default_factory=datetime.now)


# ------------------------------------------------------------------
# Use Cases & SRS Versioning
# ------------------------------------------------------------------

@dataclass
class UseCase:
    id: str
    name: str
    actor: str
    description: str
    related_requirements: List[str] = field(default_factory=list)
    preconditions: List[str] = field(default_factory=list)
    steps: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)


@dataclass
class SRSVersion:
    """Versionado formal del SRS."""
    version: str
    created_by: str
    created_at: datetime = field(default_factory=datetime.now)
    change_log: List[str] = field(default_factory=list)


@dataclass
class SoftwareRequirementsSpec:
    id: str
    project_name: str
    current_version: SRSVersion
    requirements: List[Requirement] = field(default_factory=list)
    use_cases: List[UseCase] = field(default_factory=list)
    glossary: Dict[str, str] = field(default_factory=dict)
    assumptions: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)


# ------------------------------------------------------------------
# Traceability (auditoría extremo a extremo)
# ------------------------------------------------------------------

@dataclass
class TraceabilityEntry:
    requirement_id: str
    design_artifact: str
    development_artifact: str
    test_artifact: str
    status: str


@dataclass
class TraceabilityMatrix:
    srs_id: str
    entries: List[TraceabilityEntry] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)


# ------------------------------------------------------------------
# Approval Flow
# ------------------------------------------------------------------

@dataclass
class ApprovalRequest:
    request_id: str
    srs_id: str
    requested_by: str
    requested_at: datetime = field(default_factory=datetime.now)
    comments: Optional[str] = None


@dataclass
class ApprovalResponse:
    request_id: str
    status: ApprovalStatus
    reviewed_by: str
    reviewed_at: datetime = field(default_factory=datetime.now)
    comments: Optional[str] = None


# ------------------------------------------------------------------
# Handoff & Quality Analysis
# ------------------------------------------------------------------

@dataclass
class DesignHandoffPackage:
    srs_id: str
    version: str
    requirements: List[Requirement]
    use_cases: List[UseCase]
    traceability_matrix: Optional[TraceabilityMatrix]
    notes: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class AmbiguityFlag:
    requirement_id: str
    term: str
    context: str
    severity: str


@dataclass
class AmbiguityReport:
    srs_id: str
    flags: List[AmbiguityFlag] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)
