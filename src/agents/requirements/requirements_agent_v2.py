
"""SDLAS — Requirements Agent v2 

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

from .requirements_config import get_config
from .requirements_llm import RequirementsLLMEngine
from .requirements_memory import RequirementsMemory
from .requirements_models import (
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

from .requirements_assumptions import AssumptionReviewSession

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
            req_type_str = it.get('type') or it.get('req_type') or 'functional'
            out.append(Requirement(
                id=rid,
                title=it.get('title', ''),
                description=it.get('description', ''),
                type=RequirementType(req_type_str),
                priority=PriorityLevel(it.get('priority', 'medium')),
                source=it.get('source', 'user'),
                acceptance_criteria=list(it.get('acceptance_criteria', []) or []),
                dependencies=list(it.get('dependencies', []) or []),
                status=RequirementStatus(it.get('status', 'pending')),
                ambiguity_score=float(it.get('ambiguity_score', 0.0) or 0.0),
                complexity_level=ComplexityLevel(it.get('complexity_level', 'medium')),
                tags=list(it.get('tags', []) or []),
                risks=list(it.get('risks', []) or []),
                priority_score=float(it.get('priority_score', 0.0) or 0.0),
            ))
            continue
        raise TypeError(f"Tipo de requisito no soportado: {type(it)}")
    return out

# -------------------------------------------------------------------------
# Agente v2
# -------------------------------------------------------------------------

class RequirementsAgentV2(BaseAgent):
    """Agente de requisitos con revisión de supuestos interactiva y capacidades de aprendizaje."""

    def __init__(self) -> None:
        super().__init__(
            agent_id='requirements',
            name='Requirements Agent V2',
            description='Agente de requisitos con Requisitos + revisión de supuestos + SRS + normalización y auto-refinamiento',
        )
        self._config = get_config()
        self._decision_engine = DecisionEngine()
        self._llm_engine = RequirementsLLMEngine(self._config) if self._config.enable_llm else None
        self._requirements_memory = RequirementsMemory() if self._config.enable_memory else None

        self._current_srs: Optional[SoftwareRequirementsSpec] = None
        self._srs_store: Dict[str, SoftwareRequirementsSpec] = {}
        self._knowledge_graph: Dict[str, Dict[str, Any]] = {}
        self._feedback_history: List[Dict[str, Any]] = []

        # Motor simple de refinamiento (mínimo, sin dependencias)
        self._skill_stats: Dict[str, Dict[str, Any]] = {}
        # Sesiones de revisión de supuestos (por session_id)
        self._assumption_sessions: Dict[str, AssumptionReviewSession] = {}

        self._register_capabilities()

    def _register_capabilities(self) -> None:
        caps: List[Tuple[str, str]] = [
            ('gather_requirements', 'Recopilar requisitos'),
            ('validate_assumptions', 'Listar supuestos asumidos'),
            ('assumptions_select', 'Seleccionar supuestos a redefinir'),
            ('assumptions_answer', 'Responder redefinición de supuesto'),
            ('analyze_requirements', 'Analizar requisitos'),
            ('validate_requirements', 'Validar requisitos'),
            ('generate_srs', 'Generar SRS'),
            ('create_use_cases', 'Crear casos de uso'),
            ('refine_procedures', 'Refinar procedimientos automáticamente'),
            ('run_full_pipeline', 'Ejecutar pipeline completo de requisitos'),
            ('detect_conflicts', 'Detectar conflictos y duplicados'),
            ('prioritize_requirements', 'Priorizar requisitos'),
            ('learn_from_feedback', 'Aprender de la retroalimentación'),
            ('get_agent_metrics', 'Obtener métricas del agente'),
            ('search_similar_requirements', 'Buscar requisitos similares en memoria'),
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
            'validate_assumptions': self._validate_assumptions,
            'assumptions_select': self._assumptions_select,
            'assumptions_answer': self._assumptions_answer,
            'analyze_requirements': self._analyze_requirements,
            'validate_requirements': self._validate_requirements,
            'generate_srs': self._generate_srs,
            'create_use_cases': self._create_use_cases,
            'refine_procedures': self._refine_procedures,
            'run_full_pipeline': self._run_full_pipeline,
            'detect_conflicts': self._detect_conflicts,
            'prioritize_requirements': self._prioritize_requirements,
            'learn_from_feedback': self._learn_from_feedback,
            'get_agent_metrics': self._get_agent_metrics,
            'search_similar_requirements': self._search_similar_requirements,
        }.get(task_type)

    def _record_skill(self, name: str, success: bool, seconds: float, err: str = '') -> None:
        s = self._skill_stats.setdefault(name, {
            'exec': 0,
            'ok': 0,
            'fail': 0,
            'total_time': 0.0,
            'last_error': '',
            'feedback': [],
        })
        s['exec'] += 1
        s['total_time'] += float(seconds)
        if success:
            s['ok'] += 1
        else:
            s['fail'] += 1
            s['last_error'] = err

    async def _run_full_pipeline(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        project_name = input_data.get('project_name', 'Nuevo Proyecto')
        project_description = input_data.get('project_description', '')
        requirements = normalize_requirements(input_data.get('requirements', []))
        constraints = list(input_data.get('constraints', []) or [])
        assumptions = list(input_data.get('assumptions', []) or [])
        glossary = input_data.get('glossary', {}) or {}

        if project_description and not requirements:
            if self._llm_engine:
                extracted = await self._llm_engine.extract_requirements(project_description)
            else:
                extracted = {
                    'requirements': [],
                    'glossary': {},
                    'constraints': [],
                    'assumptions': [],
                }
            requirements = normalize_requirements(extracted.get('requirements', []))
            constraints = list(extracted.get('constraints', []) or [])
            assumptions = list(extracted.get('assumptions', []) or [])
            glossary = extracted.get('glossary', {}) or {}

        self._knowledge_graph = {
            req.id: {
                'title': req.title,
                'dependencies': list(req.dependencies),
                'priority': req.priority.value,
                'type': req.type.value,
                'status': req.status.value,
            }
            for req in requirements
        }

        analysis = await self._analyze_requirements({'requirements': [self._req_to_dict(r) for r in requirements]})
        validation = await self._validate_requirements({'requirements': [self._req_to_dict(r) for r in requirements]})
        conflicts = await self._detect_conflicts({'requirements': [self._req_to_dict(r) for r in requirements]})
        prioritization = await self._prioritize_requirements({'requirements': [self._req_to_dict(r) for r in requirements]})
        srs = await self._generate_srs({
            'project_name': project_name,
            'requirements': [self._req_to_dict(r) for r in requirements],
            'constraints': constraints,
            'assumptions': assumptions,
        })
        use_cases = await self._create_use_cases({'requirements': [self._req_to_dict(r) for r in requirements]})

        if self._requirements_memory:
            for req in requirements:
                try:
                    self._requirements_memory.store_requirement(req)
                except Exception as exc:
                    logger.warning('No se pudo almacenar requisito en memoria: %s', exc)

        return {
            'project_name': project_name,
            'requirements_count': len(requirements),
            'analysis': analysis,
            'validation': validation,
            'conflicts': conflicts,
            'prioritization': prioritization,
            'srs': srs,
            'use_cases': use_cases,
            'glossary': glossary,
            'constraints': constraints,
            'assumptions': assumptions,
            'knowledge_graph': self._knowledge_graph,
        }

    async def _detect_conflicts(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        requirements = normalize_requirements(input_data.get('requirements', []))
        issues: List[Dict[str, Any]] = []
        seen_ids = set()
        title_index: Dict[str, str] = {}

        for r in requirements:
            if r.id in seen_ids:
                issues.append({'type': 'duplicate_id', 'requirement_id': r.id, 'severity': 'high'})
            else:
                seen_ids.add(r.id)

            title_key = r.title.strip().lower()
            if title_key and title_key in title_index:
                issues.append({
                    'type': 'duplicate_title',
                    'requirement_id': r.id,
                    'duplicate_of': title_index[title_key],
                    'severity': 'medium',
                })
            elif title_key:
                title_index[title_key] = r.id

            if r.id in r.dependencies:
                issues.append({'type': 'self_dependency', 'requirement_id': r.id, 'severity': 'critical'})

        def _has_cycle(node_id: str, visited: set[str], stack: set[str]) -> bool:
            if node_id not in dependency_graph:
                return False
            visited.add(node_id)
            stack.add(node_id)
            for dep in dependency_graph[node_id]:
                if dep not in visited and _has_cycle(dep, visited, stack):
                    return True
                if dep in stack:
                    return True
            stack.remove(node_id)
            return False

        dependency_graph = {r.id: set(r.dependencies) for r in requirements}
        for req_id in dependency_graph:
            if _has_cycle(req_id, set(), set()):
                issues.append({'type': 'circular_dependency', 'requirement_id': req_id, 'severity': 'critical'})

        if self._requirements_memory:
            for req in requirements:
                duplicates = self._requirements_memory.detect_duplicates(req)
                for duplicate in duplicates:
                    issues.append({
                        'type': 'possible_duplicate',
                        'requirement_id': req.id,
                        'duplicate_reference': duplicate.get('metadata', {}).get('req_id'),
                        'similarity': duplicate.get('similarity'),
                        'severity': 'medium',
                    })

        return {
            'conflicts': issues,
            'conflict_count': len(issues),
        }

    async def _prioritize_requirements(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        requirements = normalize_requirements(input_data.get('requirements', []))
        priority_score_map = {
            PriorityLevel.MUST: 1.0,
            PriorityLevel.SHOULD: 0.8,
            PriorityLevel.COULD: 0.6,
            PriorityLevel.WONT: 0.2,
            PriorityLevel.CRITICAL: 0.95,
            PriorityLevel.HIGH: 0.8,
            PriorityLevel.MEDIUM: 0.6,
            PriorityLevel.LOW: 0.4,
        }

        for r in requirements:
            base_score = priority_score_map.get(r.priority, 0.5)
            ambiguity_penalty = min(0.25, r.ambiguity_score * 0.2)
            dependency_bonus = min(0.1, len(r.dependencies) * 0.02)
            r.priority_score = round(max(0.0, base_score - ambiguity_penalty + dependency_bonus), 4)

        ordered = sorted(requirements, key=lambda x: x.priority_score, reverse=True)
        return {
            'requirements': [self._req_to_dict(r) for r in ordered],
            'priority_order': [r.id for r in ordered],
        }

    async def _learn_from_feedback(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        feedback = input_data.get('feedback', {})
        task_type = feedback.get('task_type') or input_data.get('task_type')
        rating = feedback.get('rating')
        comments = feedback.get('comments', '')
        record = {
            'task_type': task_type,
            'rating': rating,
            'comments': comments,
            'timestamp': time.monotonic(),
        }
        self._feedback_history.append(record)

        if task_type:
            skill = self._skill_stats.setdefault(task_type, {'exec': 0, 'ok': 0, 'fail': 0, 'total_time': 0.0, 'last_error': '', 'feedback': []})
            if rating is not None:
                skill['feedback'].append(rating)

        learned = {
            'stored_feedback': True,
            'feedback_count': len(self._feedback_history),
            'adaptive_changes': {
                'auto_approve_threshold': self._config.auto_approve_threshold,
                'enable_memory': self._config.enable_memory,
            },
        }
        return learned

    async def _get_agent_metrics(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'agent_id': self.agent_id,
            'state': self.state.value,
            'tasks_completed': self.metrics.tasks_completed,
            'tasks_failed': self.metrics.tasks_failed,
            'average_execution_time': self.metrics.average_execution_time,
            'last_execution': self.metrics.last_execution.isoformat() if self.metrics.last_execution else None,
            'skill_stats': self._skill_stats,
            'feedback_history_count': len(self._feedback_history),
            'memory_stats': self._requirements_memory.stats() if self._requirements_memory else None,
        }

    async def _search_similar_requirements(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self._requirements_memory:
            return {
                'error': 'Memory backend not enabled',
                'results': [],
            }
        query = str(input_data.get('query', '')).strip()
        if not query:
            return {'error': 'Query is required', 'results': []}
        results = self._requirements_memory.search_similar(query, top_k=int(input_data.get('top_k', 5)))
        return {
            'query': query,
            'results': results,
        }

    # -------------------- Capabilities --------------------

    async def _gather_requirements(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        requirements = normalize_requirements(input_data.get('requirements', []))
        if not requirements and input_data.get('project_description'):
            project_description = str(input_data.get('project_description', '')).strip()
            if project_description and self._llm_engine:
                extracted = await self._llm_engine.extract_requirements(project_description)
                requirements = normalize_requirements(extracted.get('requirements', []))

        return {
            'requirements': [self._req_to_dict(r) for r in requirements],
            'count': len(requirements),
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
        """Genera SRS SOLO cuando la sesión de supuestos está completa (si existe)."""
        project_name = input_data.get('project_name', 'Nuevo Proyecto')
        requirements = normalize_requirements(input_data.get('requirements', []))

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
            requirements=requirements,
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
