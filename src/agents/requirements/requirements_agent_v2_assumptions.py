
"""SDLAS — Requirements Agent v2 (ajustado)

Ajustes solicitados:
1) Validación y listado de supuestos (assumptions) que el agente está asumiendo.
2) El usuario selecciona por número cuáles supuestos no le gustan (o elige 'Otra').
3) Se pregunta uno a uno para redefinirlos; cada pregunta muestra barra de progreso.
4) Al finalizar, el agente indica que está listo para crear la especificación.

NOTA:
- Para inputs internos (dataclasses) NO se usa .get().
- .get() solo en input_data (dict) antes de normalizar.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from src.agents.base.base_agent import BaseAgent, AgentState, Task, TaskResult, TaskStatus, Capability
from src.agents.base.decision_engine import DecisionEngine, DecisionType, CostBenefitRule

from requirements_models import (
    Requirement, UseCase, SoftwareRequirementsSpec,
    RequirementType, RequirementStatus, PriorityLevel, ComplexityLevel,
    ApprovalStatus, SRSVersion,
)

from requirements_assumptions import AssumptionReviewSession

logger = logging.getLogger(__name__)


# ------------------------- Normalización -------------------------

def normalize_requirements(items: Any) -> List[Requirement]:
    """Normaliza requisitos (dicts u objetos) a List[Requirement]."""
    from collections.abc import Mapping, Iterable

    if items is None:
        return []
    if isinstance(items, Requirement):
        return [items]
    if isinstance(items, Mapping):
        items = [items]
    if not isinstance(items, Iterable) or isinstance(items, (str, bytes)):
        raise TypeError(f"normalize_requirements espera iterable, recibió {type(items)}")

    out: List[Requirement] = []
    for it in items:
        if isinstance(it, Requirement):
            out.append(it)
            continue
        if isinstance(it, Mapping):
            rid = it.get('id') or f"REQ-{uuid.uuid4().hex[:8].upper()}"
            out.append(Requirement(
                id=rid,
                title=it.get('title', ''),
                description=it.get('description', ''),
                type=RequirementType(it.get('type', 'functional')),
                priority=PriorityLevel(it.get('priority', 'medium')),
                source=it.get('source', 'user'),
                acceptance_criteria=list(it.get('acceptance_criteria', []) or []),
                dependencies=list(it.get('dependencies', []) or []),
                status=RequirementStatus(it.get('status', 'pending')),
                ambiguity_score=float(it.get('ambiguity_score', 0.0) or 0.0),
                complexity_level=ComplexityLevel(it.get('complexity_level', 'medium')),
            ))
            continue
        raise TypeError(f"Tipo de requisito no soportado: {type(it)}")
    return out


class RequirementsAgentV2(BaseAgent):
    """Agente de requisitos con revisión de supuestos interactiva."""

    def __init__(self) -> None:
        super().__init__(
            agent_id='requirements',
            name='Requirements Agent V2',
            description='Requisitos + revisión de supuestos + SRS',
        )
        self._decision_engine = DecisionEngine()
        self._current_srs: Optional[SoftwareRequirementsSpec] = None
        self._srs_store: Dict[str, SoftwareRequirementsSpec] = {}

        # Sesiones de revisión de supuestos (por session_id)
        self._assumption_sessions: Dict[str, AssumptionReviewSession] = {}

        self._register_capabilities()

    def _register_capabilities(self) -> None:
        caps: List[Tuple[str, str]] = [
            ('gather_requirements', 'Recopilar requisitos'),
            ('validate_assumptions', 'Listar supuestos asumidos'),
            ('assumptions_select', 'Seleccionar supuestos a redefinir'),
            ('assumptions_answer', 'Responder redefinición de supuesto'),
            ('generate_srs', 'Generar SRS'),
        ]
        for name, desc in caps:
            self.add_capability(Capability(name=name, description=desc, version='2.1.0'))

    async def initialize(self) -> None:
        self.update_state(AgentState.INITIALIZING)
        try:
            self._decision_engine.register_rule(
                DecisionType.TASK_SELECTION,
                CostBenefitRule(cost_weight=0.3, benefit_weight=0.7),
            )
        except Exception as exc:
            logger.error('Error registering decision rule: %s', exc)
        self.update_state(AgentState.IDLE)

    async def shutdown(self) -> None:
        self.update_state(AgentState.SHUTTING_DOWN)
        self.update_state(AgentState.IDLE)

    async def execute(self, task: Task) -> TaskResult:
        start = time.monotonic()
        self.update_state(AgentState.PROCESSING)
        try:
            handler = self._get_handler(task.type)
            if handler is None:
                raise ValueError(f"Unknown task type: {task.type}")
            out = await handler(task.input_data)
            elapsed = time.monotonic() - start
            self.update_metrics(elapsed, success=True)
            self.update_state(AgentState.IDLE)
            return TaskResult(task_id=task.id, status=TaskStatus.COMPLETED, output_data=out, execution_time=elapsed)
        except Exception as exc:
            elapsed = time.monotonic() - start
            self.update_metrics(elapsed, success=False)
            self.update_state(AgentState.ERROR)
            return TaskResult(task_id=task.id, status=TaskStatus.FAILED, error=str(exc), execution_time=elapsed)

    def _get_handler(self, task_type: str):
        return {
            'gather_requirements': self._gather_requirements,
            'validate_assumptions': self._validate_assumptions,
            'assumptions_select': self._assumptions_select,
            'assumptions_answer': self._assumptions_answer,
            'generate_srs': self._generate_srs,
        }.get(task_type)

    # ------------------------- capabilities -------------------------

    async def _gather_requirements(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # Implementación base (placeholder): retorna requisitos normalizados
        reqs = normalize_requirements(input_data.get('requirements', []))
        return {
            'requirements': [self._req_to_dict(r) for r in reqs],
            'count': len(reqs),
        }

    def _collect_assumptions(self, input_data: Dict[str, Any], requirements: List[Requirement]) -> List[str]:
        """Construye lista de supuestos asumidos por el agente.

        Regla:
        - Si input_data trae 'assumptions', se respetan.
        - Si no, se generan supuestos por defecto que el agente suele asumir.
        - Además, añade supuestos derivados de requisitos (p.ej. si hay performance).
        """
        raw = input_data.get('assumptions')
        assumptions: List[str] = []
        if isinstance(raw, list):
            assumptions.extend([str(x).strip() for x in raw if str(x).strip()])
        elif isinstance(raw, str) and raw.strip():
            assumptions.append(raw.strip())

        if not assumptions:
            assumptions = [
                "Existe disponibilidad de usuarios/stakeholders para validar requisitos.",
                "Se tendrá acceso a los sistemas/servicios actuales necesarios para integración.",
                "El entorno objetivo contará con conectividad de red estable.",
                "Se dispondrá de credenciales y permisos para pruebas en ambientes no productivos.",
                "Las reglas de negocio clave serán provistas por el usuario durante el levantamiento.",
            ]

        # Derivar supuestos según requisitos
        for r in requirements:
            desc = (r.description or "").lower()
            if any(k in desc for k in ("segundo", "latencia", "p95", "rendimiento", "500ms")):
                assumptions.append("Se dispone de métricas/criterios de rendimiento cuantificables (p.ej. p95) para aceptación.")
                break

        # Unificar sin duplicados
        seen = set()
        uniq = []
        for a in assumptions:
            if a not in seen:
                uniq.append(a)
                seen.add(a)
        return uniq

    async def _validate_assumptions(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Crea sesión y lista supuestos."""
        reqs = normalize_requirements(input_data.get('requirements', []))
        assumptions = self._collect_assumptions(input_data, reqs)
        session = AssumptionReviewSession(assumptions)
        self._assumption_sessions[session.session_id] = session
        payload = session.start()
        # agregar recordatorio final
        payload['next_step'] = "Responde con los números que NO te gustan (o 0 si todos están bien)."
        return payload

    async def _assumptions_select(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        session_id = str(input_data.get('session_id', '')).strip()
        selection = str(input_data.get('selection', '')).strip()
        if not session_id or session_id not in self._assumption_sessions:
            raise ValueError('session_id inválido o sesión no encontrada')
        session = self._assumption_sessions[session_id]
        return session.apply_selection(selection)

    async def _assumptions_answer(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        session_id = str(input_data.get('session_id', '')).strip()
        answer = str(input_data.get('answer', '')).strip()
        if not session_id or session_id not in self._assumption_sessions:
            raise ValueError('session_id inválido o sesión no encontrada')
        session = self._assumption_sessions[session_id]
        return session.answer_current(answer)

    async def _generate_srs(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Genera SRS SOLO cuando la sesión de supuestos está completa (si existe)."""
        project_name = input_data.get('project_name', 'Nuevo Proyecto')
        reqs = normalize_requirements(input_data.get('requirements', []))

        session_id = str(input_data.get('assumptions_session_id', '')).strip()
        assumptions: List[str] = []
        if session_id:
            session = self._assumption_sessions.get(session_id)
            if session and not session.completed:
                return {
                    'error': 'Aún no se han confirmado los supuestos.',
                    'message': 'Completa primero la revisión de supuestos. Luego estaré listo para crear la especificación.',
                    'session_id': session_id,
                }
            if session:
                # extraer supuestos finales (sin el ítem "Otra" vacío)
                for item in session.items:
                    if item.text.lower().startswith('otra') and not item.user_definition:
                        continue
                    assumptions.append(item.text)

        srs = SoftwareRequirementsSpec(
            id=f"SRS-{uuid.uuid4().hex[:8].upper()}",
            project_name=project_name,
            current_version=SRSVersion(version='1.0.0', created_by='requirements_agent'),
            requirements=reqs,
            use_cases=[],
            glossary={'API': 'Application Programming Interface', 'CRUD': 'Create, Read, Update, Delete', 'SRS': 'Software Requirements Specification'},
            assumptions=assumptions,
            constraints=list(input_data.get('constraints', []) or []),
            approval_status=ApprovalStatus.PENDING,
        )
        self._current_srs = srs
        self._srs_store[srs.id] = srs

        return {
            'message': 'SRS generado. (En flujo real se solicitaría aprobación antes del handoff a diseño).',
            'srs_id': srs.id,
            'project_name': srs.project_name,
            'version': srs.current_version.version,
            'requirements_count': len(srs.requirements),
            'assumptions': assumptions,
        }

    # ------------------------- serializers -------------------------

    @staticmethod
    def _req_to_dict(r: Requirement) -> Dict[str, Any]:
        return {
            'id': r.id,
            'title': r.title,
            'description': r.description,
            'type': r.type.value,
            'priority': r.priority.value,
            'source': r.source,
            'acceptance_criteria': list(r.acceptance_criteria),
            'dependencies': list(r.dependencies),
            'status': r.status.value,
            'ambiguity_score': r.ambiguity_score,
            'complexity_level': r.complexity_level.value,
            'created_at': r.created_at.isoformat(),
            'updated_at': r.updated_at.isoformat(),
        }

    def get_current_srs(self) -> Optional[SoftwareRequirementsSpec]:
        return self._current_srs

    def get_srs_store(self) -> Dict[str, SoftwareRequirementsSpec]:
        return self._srs_store
