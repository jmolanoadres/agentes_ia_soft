
"""SDLAS — Requirements Agent v2 (corregido)

Cambios clave:
- Eliminados accesos .get() indebidos sobre objetos dataclass (Requirement, UseCase, SRS, etc.).
- Añadida función normalize_requirements() para estandarizar inputs (dicts u objetos).

Este agente se alinea con las interfaces del repo:
- src.agents.base.base_agent.BaseAgent / Task / TaskResult / Capability
- src.agents.base.decision_engine.DecisionEngine

"""

from __future__ import annotations

import re
import logging
import time
import uuid
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Iterable, Mapping, Tuple, Union

from src.agents.base.base_agent import BaseAgent, AgentState, Task, TaskResult, TaskStatus, Capability
from src.agents.base.decision_engine import DecisionEngine, DecisionType, CostBenefitRule, DecisionOption

from requirements_models import (
    Requirement, UseCase, SoftwareRequirementsSpec,
    RequirementChange, SRSVersion,
    TraceabilityEntry, TraceabilityMatrix,
    ApprovalRequest, ApprovalResponse,
    DesignHandoffPackage,
    AmbiguityReport, AmbiguityFlag,
    RequirementType, RequirementStatus,
    PriorityLevel, ComplexityLevel,
    ApprovalStatus,
)

from requirements_assumptions import AssumptionReviewSession

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------------
# Normalización de inputs
# -------------------------------------------------------------------------

def _coerce_enum(enum_cls, value, default):
    """Convierte strings/Enum a enum_cls, con fallback seguro."""
    if value is None:
        return default
    try:
        # ya es enum
        if isinstance(value, enum_cls):
            return value
        # valor str
        if isinstance(value, str):
            v = value.strip().lower()
            # buscar por value
            for e in enum_cls:
                if str(getattr(e, 'value', '')).lower() == v:
                    return e
                # también soporta name
                if str(getattr(e, 'name', '')).lower() == v:
                    return e
        # intentar construir
        return enum_cls(value)
    except Exception:
        return default


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

# -------------------------------------------------------------------------
# Agente v2
# -------------------------------------------------------------------------

class RequirementsAgentV2(BaseAgent):
    """Agente de Requisitos v2 sin .get() indebidos."""

    def __init__(self) -> None:
        super().__init__(
            agent_id='requirements',
            name='Requirements Agent V2',
            description='Agente de requisitos con normalización y auto-refinamiento',
        )
        self._decision_engine = DecisionEngine()
        self._current_srs: Optional[SoftwareRequirementsSpec] = None
        self._srs_store: Dict[str, SoftwareRequirementsSpec] = {}

        # Motor simple de refinamiento (mínimo, sin dependencias)
        self._skill_stats: Dict[str, Dict[str, Any]] = {}

        self._register_capabilities()

    def _register_capabilities(self) -> None:
        caps: List[Tuple[str, str]] = [
            ('gather_requirements', 'Recopilar requisitos'),
            ('analyze_requirements', 'Analizar requisitos'),
            ('validate_requirements', 'Validar requisitos'),
            ('generate_srs', 'Generar SRS'),
            ('create_use_cases', 'Crear casos de uso'),
            ('refine_procedures', 'Refinar procedimientos automáticamente'),
        ]
        for name, desc in caps:
            self.add_capability(Capability(name=name, description=desc, version='2.0.0'))

    async def initialize(self) -> None:
        self.update_state(AgentState.INITIALIZING)
        logger.info('Initializing %s', self._name)
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
            self._record_skill(task.type, True, elapsed)
            self.update_state(AgentState.IDLE)
            return TaskResult(task_id=task.id, status=TaskStatus.COMPLETED, output_data=out, execution_time=elapsed)
        except Exception as exc:
            elapsed = time.monotonic() - start
            self.update_metrics(elapsed, success=False)
            self._record_skill(task.type, False, elapsed, str(exc))
            self.update_state(AgentState.ERROR)
            return TaskResult(task_id=task.id, status=TaskStatus.FAILED, error=str(exc), execution_time=elapsed)

    def _get_handler(self, task_type: str):
        return {
            'gather_requirements': self._gather_requirements,
            'analyze_requirements': self._analyze_requirements,
            'validate_requirements': self._validate_requirements,
            'generate_srs': self._generate_srs,
            'create_use_cases': self._create_use_cases,
            'refine_procedures': self._refine_procedures,
        }.get(task_type)

    def _record_skill(self, name: str, success: bool, seconds: float, err: str = '') -> None:
        s = self._skill_stats.setdefault(name, {'exec': 0, 'ok': 0, 'fail': 0, 'total_time': 0.0, 'last_error': ''})
        s['exec'] += 1
        s['total_time'] += float(seconds)
        if success:
            s['ok'] += 1
        else:
            s['fail'] += 1
            s['last_error'] = err

    # -------------------- Capabilities --------------------

    async def _gather_requirements(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # input_data es dict -> .get permitido
        text = input_data.get('project_description', '')
        source = input_data.get('source', 'user')

        # heurística simple de extracción
        parts = [p.strip() for p in re.split(r"|\.|;", text) if p.strip()]
        if not parts:
            parts = [
                'El sistema debe permitir autenticación de usuarios',
                'El sistema debe permitir operaciones CRUD',
                'El sistema debe responder en menos de 2 segundos',
            ]

        reqs: List[Requirement] = []
        for p in parts[:25]:
            rtype = RequirementType.NON_FUNCTIONAL if any(k in p.lower() for k in ['segundo', 'latencia', 'p95', 'rendimiento', 'disponibilidad']) else RequirementType.FUNCTIONAL
            prio = PriorityLevel.HIGH if 'debe' in p.lower() else PriorityLevel.MEDIUM
            reqs.append(Requirement(
                id=f"REQ-{uuid.uuid4().hex[:8].upper()}",
                title=p[:60] + ('…' if len(p) > 60 else ''),
                description=p,
                type=rtype,
                priority=prio,
                source=source,
                acceptance_criteria=[
                    f"DADO contexto válido CUANDO se ejecuta '{p[:40]}' ENTONCES el sistema responde correctamente",
                    "DADO entrada inválida CUANDO se ejecuta la operación ENTONCES el sistema retorna error controlado",
                ],
                dependencies=[],
                status=RequirementStatus.PENDING,
                ambiguity_score=0.0,
                complexity_level=ComplexityLevel.MEDIUM,
            ))

        return {
            'requirements': [self._req_to_dict(r) for r in reqs],
            'count': len(reqs),
            'project_description': text,
        }

    async def _analyze_requirements(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        requirements = normalize_requirements(input_data.get('requirements', []))
        issues: List[Dict[str, Any]] = []

        for r in requirements:
            # r es Requirement -> NO usar .get
            if not r.description:
                issues.append({'type': 'missing_description', 'requirement_id': r.id, 'severity': 'high'})
            if len(r.acceptance_criteria) < 2:
                issues.append({'type': 'missing_acceptance_criteria', 'requirement_id': r.id, 'severity': 'medium'})
            if r.id in r.dependencies:
                issues.append({'type': 'circular_dependency', 'requirement_id': r.id, 'severity': 'critical'})

        completeness = max(0, 100 - len(issues) * 10)
        return {
            'issues': issues,
            'completeness_score': completeness,
            'analyzed_count': len(requirements),
        }

    async def _validate_requirements(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        requirements = normalize_requirements(input_data.get('requirements', []))
        results = []
        for r in requirements:
            problems: List[str] = []
            if not r.id:
                problems.append('Missing ID')
            if len(r.description or '') < 20:
                problems.append('Description too short')
            if len(r.acceptance_criteria) < 2:
                problems.append('Insufficient acceptance criteria')
            results.append({'requirement_id': r.id, 'valid': len(problems) == 0, 'issues': problems})

        valid_count = sum(1 for x in results if x['valid'])
        total = len(results)
        return {
            'validation_results': results,
            'total': total,
            'valid': valid_count,
            'invalid': total - valid_count,
            'validation_rate': (valid_count / total) if total else 0.0,
        }

    async def _generate_srs(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        project_name = input_data.get('project_name', 'Nuevo Proyecto')
        requirements = normalize_requirements(input_data.get('requirements', []))

        srs = SoftwareRequirementsSpec(
            id=f"SRS-{uuid.uuid4().hex[:8].upper()}",
            project_name=project_name,
            current_version=SRSVersion(version='1.0.0', created_by='requirements_agent'),
            requirements=requirements,
            use_cases=[],
            glossary={'API': 'Application Programming Interface', 'CRUD': 'Create, Read, Update, Delete', 'SRS': 'Software Requirements Specification'},
            assumptions=['Recursos suficientes para desarrollo'],
            constraints=['Presupuesto limitado', 'Timeline de 3 meses'],
            approval_status=ApprovalStatus.PENDING,
        )
        self._current_srs = srs
        self._srs_store[srs.id] = srs
        return {'srs_id': srs.id, 'project_name': srs.project_name, 'version': srs.current_version.version, 'requirements_count': len(srs.requirements)}

    async def _create_use_cases(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # Normalizar: dentro, usar atributos
        requirements = normalize_requirements(input_data.get('requirements', []))
        use_cases: List[UseCase] = []

        for r in requirements:
            if r.type == RequirementType.FUNCTIONAL:
                title = r.title or 'Unknown'
                uc = UseCase(
                    id=f"UC-{uuid.uuid4().hex[:8].upper()}",
                    name=f"UC-{title.replace(' ', '_')[:30]}",
                    actor='Usuario',
                    description=r.description,
                    related_requirements=[r.id] if r.id else [],
                    preconditions=['Usuario autenticado'],
                    steps=[
                        f"1. Usuario inicia acción: {title}",
                        '2. Sistema valida solicitud',
                        '3. Sistema procesa y retorna resultado',
                    ],
                    postconditions=['Operación completada'],
                )
                use_cases.append(uc)

        return {
            'use_cases': [self._use_case_to_dict(u) for u in use_cases],
            'count': len(use_cases),
        }

    async def _refine_procedures(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        # ejemplo mínimo: recomendar según stats
        report = {}
        for name, s in self._skill_stats.items():
            rate = (s['ok'] / s['exec']) if s['exec'] else 1.0
            report[name] = {
                'executions': s['exec'],
                'success_rate': round(rate, 4),
                'avg_time': round((s['total_time'] / s['exec']) if s['exec'] else 0.0, 4),
                'last_error': s.get('last_error', ''),
                'recommendation': 'OK' if rate >= 0.8 else 'Revisar lógica / ampliar normalización',
            }
        return {'skills': report}

    # -------------------- Serialization helpers --------------------

    @staticmethod
    def _req_to_dict(r: Requirement) -> Dict[str, Any]:
        # acceso por atributos, no .get
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

    @staticmethod
    def _use_case_to_dict(u: UseCase) -> Dict[str, Any]:
        return {
            'id': u.id,
            'name': u.name,
            'actor': u.actor,
            'description': u.description,
            'related_requirements': list(u.related_requirements),
            'preconditions': list(u.preconditions),
            'steps': list(u.steps),
            'postconditions': list(u.postconditions),
        }

    def get_current_srs(self) -> Optional[SoftwareRequirementsSpec]:
        return self._current_srs

    def get_srs_store(self) -> Dict[str, SoftwareRequirementsSpec]:
        return self._srs_store
