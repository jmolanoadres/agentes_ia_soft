"""auto_refinement_models.py

Modelos del sistema de Auto-Refinamiento (SDLAS).

Este módulo define únicamente estructuras de datos (dataclasses) usadas por
ProcedureRefinementEngine.

Diseñado para:
- Ser auditable (historial, timestamps)
- No depender de librerías externas
- Ser estable para serialización (export/import)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class SkillRecord:
    """Tracks a single skill/capability performance.

    Attributes:
        skill_name: Nombre de la habilidad (p.ej. 'gather_requirements').
        executions: Número total de ejecuciones.
        successes: Ejecuciones exitosas.
        failures: Ejecuciones fallidas.
        avg_execution_time: Tiempo promedio (segundos).
        total_execution_time: Tiempo acumulado (segundos).
        last_feedback_score: Último score de feedback (0..1).
        improvement_notes: Notas de mejora acumuladas.
        last_executed: Timestamp de la última ejecución.
    """

    skill_name: str
    executions: int = 0
    successes: int = 0
    failures: int = 0
    avg_execution_time: float = 0.0
    total_execution_time: float = 0.0
    last_feedback_score: float = 0.0
    improvement_notes: list[str] = field(default_factory=list)
    last_executed: datetime | None = None

    @property
    def success_rate(self) -> float:
        return (self.successes / self.executions) if self.executions else 1.0

    @property
    def failure_rate(self) -> float:
        return (self.failures / self.executions) if self.executions else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_name": self.skill_name,
            "executions": self.executions,
            "successes": self.successes,
            "failures": self.failures,
            "avg_execution_time": self.avg_execution_time,
            "total_execution_time": self.total_execution_time,
            "last_feedback_score": self.last_feedback_score,
            "improvement_notes": list(self.improvement_notes),
            "last_executed": self.last_executed.isoformat() if self.last_executed else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillRecord:
        obj = cls(skill_name=data.get("skill_name", "unknown"))
        obj.executions = int(data.get("executions", 0))
        obj.successes = int(data.get("successes", 0))
        obj.failures = int(data.get("failures", 0))
        obj.avg_execution_time = float(data.get("avg_execution_time", 0.0))
        obj.total_execution_time = float(data.get("total_execution_time", 0.0))
        obj.last_feedback_score = float(data.get("last_feedback_score", 0.0))
        obj.improvement_notes = list(data.get("improvement_notes", []) or [])
        last = data.get("last_executed")
        if last:
            try:
                obj.last_executed = datetime.fromisoformat(last)
            except Exception:
                obj.last_executed = None
        return obj


@dataclass
class RefinementAction:
    """An action to refine a procedure.

    action_type valores sugeridos:
        - adjust_prompt
        - add_validation
        - optimize_pipeline
        - add_heuristic
        - escalate
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    skill_name: str = ""
    action_type: str = ""
    description: str = ""
    applied: bool = False
    impact_score: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "skill_name": self.skill_name,
            "action_type": self.action_type,
            "description": self.description,
            "applied": self.applied,
            "impact_score": self.impact_score,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RefinementAction:
        created_at = data.get("created_at")
        dt = None
        if created_at:
            try:
                dt = datetime.fromisoformat(created_at)
            except Exception:
                dt = None
        obj = cls(
            id=str(data.get("id", str(uuid.uuid4()))),
            skill_name=str(data.get("skill_name", "")),
            action_type=str(data.get("action_type", "")),
            description=str(data.get("description", "")),
            applied=bool(data.get("applied", False)),
            impact_score=float(data.get("impact_score", 0.0)),
        )
        if dt:
            obj.created_at = dt
        return obj
