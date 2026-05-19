"""
Workflow completo del Requirements Agent v2.0.
Pipeline: Gather → Analyze → Ambiguity → Prioritize → SRS → Approval → Design Handoff.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Callable
from datetime import datetime
from enum import Enum
from typing import Any

from .requirements_config import get_config
from .requirements_llm import RequirementsLLMEngine
from .requirements_models import (
    ApprovalRequest,
    ApprovalResponse,
    ApprovalStatus,
    DesignHandoffPackage,
    PriorityLevel,
    Requirement,
    RequirementStatus,
    SoftwareRequirementsSpec,
    SRSVersion,
    TraceabilityEntry,
    TraceabilityMatrix,
    UseCase,
)

logger = logging.getLogger(__name__)


class WorkflowStage(Enum):
    """Etapas del pipeline de requisitos."""

    GATHER = "gather"
    ANALYZE = "analyze"
    DETECT_AMBIGUITY = "detect_ambiguity"
    PRIORITIZE = "prioritize"
    GENERATE_SRS = "generate_srs"
    APPROVAL_GATE = "approval_gate"
    HANDOFF_TO_DESIGN = "handoff_to_design"


class WorkflowStatus(Enum):
    """Estado del workflow."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    WAITING_APPROVAL = "waiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"


# ═══════════════════════════════════════════════
#  APPROVAL GATE
# ═══════════════════════════════════════════════


class ApprovalGate:
    """
    Puerta de aprobación humana (Human-in-the-Loop).

    Pausa el pipeline y espera respuesta del usuario
    antes de hacer handoff al Design Agent.
    """

    def __init__(self, timeout_seconds: int | None = None):
        config = get_config()
        self._timeout = timeout_seconds or config.approval_timeout_seconds
        self._auto_threshold = config.auto_approve_threshold
        self._pending_requests: dict[str, ApprovalRequest] = {}
        self._responses: dict[str, ApprovalResponse] = {}
        self._response_events: dict[str, asyncio.Event] = {}
        self._callbacks: list[Callable[[ApprovalResponse], None]] = []

    def register_callback(self, callback: Callable[[ApprovalResponse], None]) -> None:
        """Registrar callback para notificaciones de aprobación."""
        self._callbacks.append(callback)

    async def request_approval(
        self,
        srs: SoftwareRequirementsSpec,
        event_bus: Any | None = None,
    ) -> ApprovalRequest:
        """
        Crear solicitud de aprobación para un SRS.

        Si el completeness_score supera el auto_threshold,
        se puede auto-aprobar.
        """
        issues = []
        ambiguity_score = getattr(srs, "ambiguity_score", 0.0)
        if ambiguity_score > 0.3:
            issues.append(f"Score de ambigüedad elevado: {ambiguity_score:.2f}")

        incomplete = [r for r in srs.requirements if not r.is_complete]
        if incomplete:
            issues.append(f"{len(incomplete)} requisitos incompletos")

        request = ApprovalRequest(
            request_id=str(uuid.uuid4()),
            srs_id=srs.id,
            srs_version=getattr(srs, "version", None)
            or getattr(getattr(srs, "current_version", None), "version", None),
            summary=(
                f"SRS '{srs.project_name}' v{srs.version} "
                f"con {len(srs.requirements)} requisitos. "
                f"Completeness: {getattr(srs, 'completeness_score', 0.0):.1f}%"
            ),
            completeness_score=getattr(srs, "completeness_score", 0.0),
            ambiguity_score=ambiguity_score,
            total_requirements=len(srs.requirements),
            issues=issues,
            requested_by="requirements_agent",
            timeout_seconds=self._timeout,
        )

        self._pending_requests[request.id] = request
        self._response_events[request.id] = asyncio.Event()

        # Emitir evento
        if event_bus:
            await event_bus.publish(
                event_bus.create_event(
                    event_type="requirements.approval_requested",
                    source="requirements_agent",
                    data=request.to_dict(),
                )
            )

        logger.info(
            f"Solicitud de aprobación creada: {request.id} "
            f"(completeness: {srs.completeness_score:.1f}%)"
        )

        # Auto-aprobación si cumple umbral
        if srs.completeness_score >= self._auto_threshold and not issues:
            logger.info(
                f"Auto-aprobación activada (score {srs.completeness_score:.1f}% "
                f">= {self._auto_threshold}%)"
            )
            auto_response = ApprovalResponse(
                request_id=request.id,
                status=ApprovalStatus.APPROVED,
                reviewed_by="auto_approval_system",
                comments="Auto-aprobado por cumplir umbral de calidad",
            )
            await self.submit_response(auto_response)

        return request

    async def wait_for_response(
        self,
        request_id: str,
        timeout: int | None = None,
    ) -> ApprovalResponse:
        """
        Esperar la respuesta del usuario.

        Bloquea hasta recibir respuesta o timeout.
        """
        timeout = timeout or self._timeout
        event = self._response_events.get(request_id)
        if not event:
            raise ValueError(f"Request no encontrado: {request_id}")

        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        except TimeoutError:
            logger.warning(f"Timeout esperando aprobación: {request_id}")
            return ApprovalResponse(
                request_id=request_id,
                status=ApprovalStatus.TIMED_OUT,
                reviewed_by="system",
                comments=f"Timeout después de {timeout}s",
            )

        return self._responses.get(
            request_id,
            ApprovalResponse(
                request_id=request_id,
                status=ApprovalStatus.TIMED_OUT,
                reviewed_by="system",
                comments="No response received before timeout",
            ),
        )

    async def submit_response(self, response: ApprovalResponse) -> None:
        """
        Enviar respuesta de aprobación (desde UI o sistema).
        """
        self._responses[response.request_id] = response

        event = self._response_events.get(response.request_id)
        if event:
            event.set()

        # Notificar callbacks
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(response)
                else:
                    callback(response)
            except Exception as e:
                logger.error(f"Error en callback de aprobación: {e}")

        logger.info(
            f"Respuesta de aprobación recibida: {response.request_id} → {response.status.value}"
        )

    def get_pending_requests(self) -> list[ApprovalRequest]:
        """Obtener solicitudes pendientes."""
        return [r for r in self._pending_requests.values() if r.id not in self._responses]


# ═══════════════════════════════════════════════
#  DESIGN HANDOFF
# ═══════════════════════════════════════════════


class DesignHandoff:
    """Prepara el paquete de entrega al Design Agent."""

    @staticmethod
    def create_package(
        srs: SoftwareRequirementsSpec,
        approval: ApprovalResponse,
        traceability: TraceabilityMatrix | None = None,
    ) -> DesignHandoffPackage:
        """Crear paquete completo para el Design Agent."""

        # Construir trazabilidad si no existe
        if traceability is None:
            traceability = TraceabilityMatrix(srs_id=srs.id)
            for req in srs.requirements:
                for uc in srs.use_cases:
                    if req.id in uc.related_requirements:
                        traceability.add_entry(
                            TraceabilityEntry(
                                source_id=req.id,
                                target_id=uc.id,
                                link_type="derives_from",
                                rationale="Caso de uso derivado de requisito",
                            )
                        )

        # Extraer constraints para diseño
        design_constraints = list(srs.constraints)
        for req in srs.requirements:
            if req.req_type.value in ("constraint", "performance", "security"):
                design_constraints.append(f"[{req.id}] {req.title}: {req.description[:100]}")

        # Orden de prioridad
        sorted_reqs = sorted(
            srs.requirements,
            key=lambda r: r.priority_score,
            reverse=True,
        )
        priority_order = [r.id for r in sorted_reqs]

        # Sugerencias de patrones
        suggested_patterns = []
        has_auth = any("auth" in r.tags for r in srs.requirements)
        has_api = any("api" in r.tags for r in srs.requirements)
        has_db = any("database" in r.tags for r in srs.requirements)

        if has_api:
            suggested_patterns.extend(["REST API", "Controller-Service-Repository"])
        if has_auth:
            suggested_patterns.extend(["JWT Authentication", "RBAC"])
        if has_db:
            suggested_patterns.extend(["Repository Pattern", "Unit of Work"])
        if len(srs.requirements) > 20:
            suggested_patterns.append("Microservices Architecture")
        else:
            suggested_patterns.append("Monolithic with Clean Architecture")

        package = DesignHandoffPackage(
            id=str(uuid.uuid4()),
            srs_id=srs.id,
            version=getattr(
                srs, "version", getattr(getattr(srs, "current_version", None), "version", "1.0.0")
            ),
            requirements=srs.requirements,
            use_cases=srs.use_cases,
            traceability_matrix=traceability,
            approval_response=approval,
            design_guidelines=[
                "Seguir principios SOLID",
                "Implementar inyección de dependencias",
                "Diseñar para testabilidad",
                "Documentar decisiones de arquitectura (ADR)",
            ],
            constraints_for_design=design_constraints,
            priority_order=priority_order,
        )

        logger.info(
            f"DesignHandoffPackage creado: {package.id} "
            f"({len(srs.requirements)} requisitos, "
            f"{len(priority_order)} priorizados)"
        )
        return package


# ═══════════════════════════════════════════════
#  WORKFLOW PRINCIPAL
# ═══════════════════════════════════════════════


class RequirementsWorkflow:
    """
    Orquestador del pipeline completo de requisitos.

    Pipeline:
        GATHER → ANALYZE → DETECT_AMBIGUITY → PRIORITIZE
        → GENERATE_SRS → APPROVAL_GATE → HANDOFF_TO_DESIGN
    """

    def __init__(
        self,
        llm_engine: RequirementsLLMEngine | None = None,
        memory: Any | None = None,
        decision_engine: Any | None = None,
        event_bus: Any | None = None,
    ) -> None:
        self._llm_engine: RequirementsLLMEngine | None = llm_engine
        self._memory: Any | None = memory
        self._decision_engine: Any | None = decision_engine
        self._event_bus: Any | None = event_bus
        self._approval_gate = ApprovalGate()
        self._design_handoff = DesignHandoff()

        self._current_stage: WorkflowStage = WorkflowStage.GATHER
        self._status: WorkflowStatus = WorkflowStatus.NOT_STARTED
        self._pipeline_data: dict[str, Any] = {}

    @property
    def current_stage(self) -> WorkflowStage:
        return self._current_stage

    @property
    def status(self) -> WorkflowStatus:
        return self._status

    @property
    def approval_gate(self) -> ApprovalGate:
        return self._approval_gate

    # ── Pipeline completo ────────────────────────

    async def run_full_pipeline(
        self,
        project_description: str,
        project_name: str = "Nuevo Proyecto",
    ) -> dict[str, Any]:
        """
        Ejecutar el pipeline completo de requisitos.

        Returns:
            Dict con SRS, approval, handoff package y métricas.
        """
        self._status = WorkflowStatus.IN_PROGRESS
        pipeline_id = str(uuid.uuid4())
        start_time = datetime.now()

        try:
            # ── STAGE 1: Gather ──
            await self._emit_event("requirements.stage.gather.started", {})
            self._current_stage = WorkflowStage.GATHER
            extracted = await self._stage_gather(project_description)
            requirements = extracted["requirements"]
            await self._emit_event(
                "requirements.stage.gather.completed",
                {"count": len(requirements)},
            )

            # ── STAGE 2: Analyze ──
            self._current_stage = WorkflowStage.ANALYZE
            await self._emit_event("requirements.stage.analyze.started", {})
            analysis = await self._stage_analyze(requirements)
            await self._emit_event(
                "requirements.stage.analyze.completed",
                {"issues": len(analysis.get("issues", []))},
            )

            # ── STAGE 3: Detect Ambiguity ──
            self._current_stage = WorkflowStage.DETECT_AMBIGUITY
            await self._emit_event("requirements.stage.ambiguity.started", {})
            requirements = await self._stage_detect_ambiguity(requirements)
            ambiguous_count = sum(1 for r in requirements if r.is_ambiguous)
            await self._emit_event(
                "requirements.stage.ambiguity.completed",
                {"ambiguous_count": ambiguous_count},
            )

            # ── STAGE 4: Prioritize ──
            self._current_stage = WorkflowStage.PRIORITIZE
            await self._emit_event("requirements.stage.prioritize.started", {})
            requirements = await self._stage_prioritize(requirements)
            await self._emit_event(
                "requirements.stage.prioritize.completed",
                {},
            )

            # ── STAGE 5: Generate SRS ──
            self._current_stage = WorkflowStage.GENERATE_SRS
            await self._emit_event("requirements.stage.srs.started", {})
            use_cases = await self._stage_generate_use_cases(requirements)
            srs = await self._stage_generate_srs(project_name, requirements, use_cases, extracted)
            await self._emit_event(
                "requirements.stage.srs.completed",
                {"srs_id": srs.id, "version": srs.version},
            )

            # ── STAGE 6: Approval Gate ──
            self._current_stage = WorkflowStage.APPROVAL_GATE
            self._status = WorkflowStatus.WAITING_APPROVAL
            await self._emit_event("requirements.stage.approval.started", {})
            approval_request = await self._approval_gate.request_approval(srs, self._event_bus)
            approval_response = await self._approval_gate.wait_for_response(approval_request.id)

            if approval_response.status == ApprovalStatus.APPROVED:
                self._status = WorkflowStatus.APPROVED
                srs.approval_status = ApprovalStatus.APPROVED
                srs.approved_by = approval_response.reviewed_by
                srs.approved_at = approval_response.responded_at
            elif approval_response.status == ApprovalStatus.CHANGES_REQUESTED:
                self._status = WorkflowStatus.REJECTED
                await self._emit_event(
                    "requirements.stage.approval.changes_requested",
                    {"changes": approval_response.change_requests},
                )
                return {
                    "pipeline_id": pipeline_id,
                    "status": "changes_requested",
                    "srs": srs.to_dict(),
                    "approval": approval_response.to_dict(),
                    "change_requests": approval_response.change_requests,
                }
            else:
                self._status = WorkflowStatus.REJECTED
                return {
                    "pipeline_id": pipeline_id,
                    "status": approval_response.status.value,
                    "srs": srs.to_dict(),
                    "approval": approval_response.to_dict(),
                }

            await self._emit_event(
                "requirements.stage.approval.completed",
                {"status": approval_response.status.value},
            )

            # ── STAGE 7: Handoff to Design ──
            self._current_stage = WorkflowStage.HANDOFF_TO_DESIGN
            await self._emit_event("requirements.stage.handoff.started", {})
            handoff_package = self._design_handoff.create_package(srs, approval_response)

            # Almacenar en memoria
            if self._memory:
                for req in requirements:
                    self._memory.store_requirement(req)

            self._status = WorkflowStatus.COMPLETED
            execution_time = (datetime.now() - start_time).total_seconds()

            await self._emit_event(
                "requirements.pipeline.completed",
                {
                    "pipeline_id": pipeline_id,
                    "execution_time": execution_time,
                    "srs_id": srs.id,
                },
            )

            return {
                "pipeline_id": pipeline_id,
                "status": "completed",
                "execution_time_seconds": execution_time,
                "srs": srs.to_dict(),
                "approval": approval_response.to_dict(),
                "handoff_package": handoff_package.to_dict(),
                "metrics": {
                    "total_requirements": len(requirements),
                    "ambiguous_count": ambiguous_count,
                    "use_cases_count": len(use_cases),
                    "completeness_score": srs.completeness_score,
                    "ambiguity_score": srs.ambiguity_score,
                },
            }

        except Exception as e:
            self._status = WorkflowStatus.FAILED
            logger.error(f"Pipeline falló en {self._current_stage.value}: {e}")
            await self._emit_event(
                "requirements.pipeline.failed",
                {"stage": self._current_stage.value, "error": str(e)},
            )
            raise

    # ── Stage implementations ────────────────────

    async def _stage_gather(self, project_description: str) -> dict[str, Any]:
        """Stage 1: Recopilar requisitos."""
        logger.info("Stage GATHER: Extrayendo requisitos...")
        if self._llm_engine:
            extracted = await self._llm_engine.extract_requirements(project_description)
        else:
            extracted = {"requirements": [], "glossary": {}, "constraints": []}

        # Convertir dicts a objetos Requirement
        requirements = []
        for req_data in extracted.get("requirements", []):
            req = Requirement.from_dict(req_data) if isinstance(req_data, dict) else req_data
            requirements.append(req)

        extracted["requirements"] = requirements
        logger.info(f"Stage GATHER completado: {len(requirements)} requisitos")
        return extracted

    async def _stage_analyze(self, requirements: list[Requirement]) -> dict[str, Any]:
        """Stage 2: Analizar coherencia y completitud."""
        logger.info("Stage ANALYZE: Analizando requisitos...")
        issues = []
        suggestions = []

        for req in requirements:
            if not req.title:
                issues.append({"req_id": req.id, "issue": "Sin título"})
            if len(req.acceptance_criteria) < 2:
                issues.append(
                    {
                        "req_id": req.id,
                        "issue": "Menos de 2 criterios de aceptación",
                    }
                )

        # Verificar dependencias circulares
        dep_graph = {r.id: set(r.dependencies) for r in requirements}
        for req_id, deps in dep_graph.items():
            if req_id in deps:
                issues.append(
                    {
                        "req_id": req_id,
                        "issue": "Dependencia circular",
                        "severity": "critical",
                    }
                )

        # Verificar balance de prioridades
        priorities = [r.priority.value for r in requirements]
        must_ratio = priorities.count("must") / len(priorities) if priorities else 0
        if must_ratio > 0.6:
            suggestions.append(
                "Más del 60% de requisitos son MUST. Considere redistribuir prioridades."
            )

        logger.info(
            f"Stage ANALYZE completado: {len(issues)} issues, {len(suggestions)} sugerencias"
        )
        return {"issues": issues, "suggestions": suggestions}

    async def _stage_detect_ambiguity(self, requirements: list[Requirement]) -> list[Requirement]:
        """Stage 3: Detectar ambigüedades."""
        logger.info("Stage DETECT_AMBIGUITY: Analizando ambigüedades...")
        for req in requirements:
            if self._llm_engine:
                report = await self._llm_engine.detect_ambiguity(req)
                req.ambiguity_report = report
                req.ambiguity_score = report.score
            req.status = RequirementStatus.ANALYZED
        return requirements

    async def _stage_prioritize(self, requirements: list[Requirement]) -> list[Requirement]:
        """Stage 4: Priorizar con DecisionEngine."""
        logger.info("Stage PRIORITIZE: Priorizando requisitos...")

        if self._decision_engine:
            from src.agents.base.decision_engine import (
                DecisionOption,
                DecisionType,
            )

            options = [
                DecisionOption(
                    id=req.id,
                    description=req.title,
                    pros=[f"Tipo: {req.req_type.value}"],
                    cons=[],
                    score=req.priority_score,
                    risk_level=getattr(req, "ambiguity_score", 0.0),
                )
                for req in requirements
            ]

            if options:
                await self._decision_engine.evaluate_options(
                    DecisionType.TASK_SELECTION,
                    context={"goal": "prioritize_requirements"},
                    options=options,
                )
                # Actualizar scores
                for opt in options:
                    for req in requirements:
                        if req.id == opt.id:
                            req.priority_score = opt.score
                            break
        else:
            # Priorización heurística
            priority_scores = {
                PriorityLevel.MUST: 0.9,
                PriorityLevel.SHOULD: 0.7,
                PriorityLevel.COULD: 0.4,
                PriorityLevel.WONT: 0.1,
            }
            for req in requirements:
                base = priority_scores.get(req.priority, 0.5)
                ambiguity_penalty = getattr(req, "ambiguity_score", 0.0) * 0.2
                req.priority_score = max(0.0, base - ambiguity_penalty)

        return sorted(requirements, key=lambda r: r.priority_score, reverse=True)

    async def _stage_generate_use_cases(self, requirements: list[Requirement]) -> list[UseCase]:
        """Generar casos de uso."""
        if self._llm_engine:
            return await self._llm_engine.generate_use_cases(requirements)
        return []

    async def _stage_generate_srs(
        self,
        project_name: str,
        requirements: list[Requirement],
        use_cases: list[UseCase],
        extracted: dict[str, Any],
    ) -> SoftwareRequirementsSpec:
        """Stage 5: Generar SRS versionado."""
        logger.info("Stage GENERATE_SRS: Generando SRS...")

        srs = SoftwareRequirementsSpec(
            id=f"SRS-{uuid.uuid4().hex[:8].upper()}",
            project_name=project_name,
            description=f"SRS generado automáticamente para {project_name}",
            version="1.0.0",
            current_version=SRSVersion(version="1.0.0", created_by="requirements_agent"),
            requirements=requirements,
            use_cases=use_cases,
            glossary=extracted.get("glossary", {}),
            assumptions=extracted.get("assumptions", []),
            constraints=extracted.get("constraints", []),
            completeness_score=100.0 - sum(1 for r in requirements if not r.is_complete) * 10.0,
            ambiguity_score=(
                sum(getattr(r, "ambiguity_score", 0.0) for r in requirements) / len(requirements)
                if requirements
                else 0.0
            ),
        )

        # Crear snapshot inicial
        srs.version_history.append(
            {
                "version": srs.version,
                "created_at": datetime.now().isoformat(),
                "summary": "Versión inicial generada automáticamente",
                "requirement_ids": [r.id for r in requirements],
            }
        )

        # Construir trazabilidad
        for req in requirements:
            for uc in use_cases:
                if req.id in uc.related_requirements:
                    srs.traceability.append(
                        TraceabilityEntry(
                            source_id=req.id,
                            target_id=uc.id,
                            link_type="derives_from",
                        )
                    )

        logger.info(
            f"SRS generado: {srs.id} v{srs.version} "
            f"({len(requirements)} reqs, {len(use_cases)} UCs)"
        )
        return srs

    # ── Event emission ───────────────────────────

    async def _emit_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Emitir evento al bus."""
        if self._event_bus:
            try:
                event = self._event_bus.create_event(
                    event_type=event_type,
                    source="requirements_agent",
                    data=data,
                )
                await self._event_bus.publish(event)
            except Exception as e:
                logger.warning(f"Error emitiendo evento {event_type}: {e}")
        logger.debug(f"Event: {event_type} → {data}")
