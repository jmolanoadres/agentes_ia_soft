"""Requirements agent for gathering and managing requirements."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from src.agents.base.base_agent import BaseAgent, AgentState, Task, TaskResult, TaskStatus, Capability
from src.agents.base.decision_engine import DecisionEngine, DecisionOption, DecisionType, DecisionConfidence

logger = logging.getLogger(__name__)


@dataclass
class Requirement:
    """Representa un requisito."""
    id: str
    title: str
    description: str
    type: str  # functional, non_functional, constraint
    priority: str  # high, medium, low
    source: str
    acceptance_criteria: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class UseCase:
    """Representa un caso de uso."""
    id: str
    name: str
    actor: str
    description: str
    preconditions: List[str] = field(default_factory=list)
    steps: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)
    alternative_flows: List[str] = field(default_factory=list)


@dataclass
class SoftwareRequirementsSpec:
    """Especificación de requisitos de software."""
    id: str
    project_name: str
    version: str
    requirements: List[Requirement] = field(default_factory=list)
    use_cases: List[UseCase] = field(default_factory=list)
    glossary: Dict[str, str] = field(default_factory=dict)
    assumptions: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


class RequirementsAgent(BaseAgent):
    """Agente especializado en gestión de requisitos."""
    
    def __init__(self):
        super().__init__(
            agent_id="requirements",
            name="Requirements Agent",
            description="Agente para recopilación, análisis y documentación de requisitos"
        )
        self._decision_engine = DecisionEngine()
        self._current_srs: Optional[SoftwareRequirementsSpec] = None
        self._requirement_store: Dict[str, SoftwareRequirementsSpec] = {}
        
        # Registrar capacidades
        self._register_capabilities()
    
    def _register_capabilities(self) -> None:
        """Registrar las capacidades del agente."""
        self.add_capability(Capability(
            name="gather_requirements",
            description="Recopilar requisitos del usuario",
            version="1.0.0"
        ))
        self.add_capability(Capability(
            name="analyze_requirements",
            description="Analizar coherencia y completitud de requisitos",
            version="1.0.0"
        ))
        self.add_capability(Capability(
            name="generate_srs",
            description="Generar especificación de requisitos de software",
            version="1.0.0"
        ))
        self.add_capability(Capability(
            name="create_use_cases",
            description="Crear casos de uso desde requisitos",
            version="1.0.0"
        ))
        self.add_capability(Capability(
            name="validate_requirements",
            description="Validar requisitos contra estándares",
            version="1.0.0"
        ))
    
    async def initialize(self) -> None:
        """Inicializar el agente."""
        self.update_state(AgentState.INITIALIZING)
        logger.info(f"Initializing {self._name}")
        
        # Inicializar motor de decisiones
        self._decision_engine.register_rule(
            DecisionType.TASK_SELECTION,
            CostBenefitRule(cost_weight=0.3, benefit_weight=0.7)
        )
        
        self.update_state(AgentState.IDLE)
        logger.info(f"{self._name} initialized successfully")
    
    async def execute(self, task: Task) -> TaskResult:
        """Ejecutar una tarea de requisitos."""
        start_time = datetime.now()
        self.update_state(AgentState.PROCESSING)
        
        try:
            task_type = task.type
            
            if task_type == "gather_requirements":
                result = await self._gather_requirements(task.input_data)
            elif task_type == "analyze_requirements":
                result = await self._analyze_requirements(task.input_data)
            elif task_type == "generate_srs":
                result = await self._generate_srs(task.input_data)
            elif task_type == "create_use_cases":
                result = await self._create_use_cases(task.input_data)
            elif task_type == "validate_requirements":
                result = await self._validate_requirements(task.input_data)
            else:
                raise ValueError(f"Unknown task type: {task_type}")
            
            execution_time = (datetime.now() - start_time).total_seconds()
            self.update_metrics(execution_time, success=True)
            self.update_state(AgentState.IDLE)
            
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                output_data=result,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.update_metrics(execution_time, success=False)
            self.update_state(AgentState.ERROR)
            logger.error(f"Error executing task: {e}")
            
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                error=str(e),
                execution_time=execution_time
            )
    
    async def _gather_requirements(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Recopilar requisitos desde descripción del proyecto."""
        project_description = input_data.get("project_description", "")
        
        # En una implementación real, esto usaría un LLM para analizar
        # la descripción y extraer requisitos
        requirements = []
        
        # Simular extracción de requisitos
        extracted_requirements = [
            Requirement(
                id=str(uuid.uuid4()),
                title="Autenticación de usuarios",
                description="El sistema debe permitir a los usuarios autenticarse",
                type="functional",
                priority="high",
                source="stakeholder",
                acceptance_criteria=[
                    "Usuario puede iniciar sesión con email y contraseña",
                    "Sistema valida credenciales",
                    "Sesión persiste entre requests"
                ]
            ),
            Requirement(
                id=str(uuid.uuid4()),
                title="Gestión de datos",
                description="El sistema debe permitir CRUD de entidades",
                type="functional",
                priority="high",
                source="stakeholder",
                acceptance_criteria=[
                    "Usuario puede crear nuevas entidades",
                    "Usuario puede leer entidades existentes",
                    "Usuario puede actualizar entidades",
                    "Usuario puede eliminar entidades"
                ]
            ),
            Requirement(
                id=str(uuid.uuid4()),
                title="Rendimiento",
                description="El sistema debe responder en menos de 2 segundos",
                type="non_functional",
                priority="medium",
                source="technical",
                acceptance_criteria=[
                    "Tiempo de respuesta promedio < 2s",
                    "Tiempo de respuesta p95 < 5s"
                ]
            ),
        ]
        
        return {
            "requirements": [self._requirement_to_dict(r) for r in extracted_requirements],
            "count": len(extracted_requirements),
            "project_description": project_description
        }
    
    async def _analyze_requirements(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analizar requisitos para detectar problemas."""
        requirements_data = input_data.get("requirements", [])
        
        issues = []
        suggestions = []
        
        # Verificar completitud
        for req in requirements_data:
            if not req.get("description"):
                issues.append({
                    "type": "missing_description",
                    "requirement": req.get("id"),
                    "severity": "high"
                })
            
            if not req.get("acceptance_criteria"):
                issues.append({
                    "type": "missing_acceptance_criteria",
                    "requirement": req.get("id"),
                    "severity": "medium"
                })
        
        # Verificar coherencia
        priorities = [r.get("priority") for r in requirements_data]
        if priorities.count("high") > len(priorities) * 0.5:
            suggestions.append({
                "type": "too_many_high_priority",
                "message": "Más del 50% de requisitos son de alta prioridad. Considere redistribuir."
            })
        
        # Verificar dependencias
        for req in requirements_data:
            deps = req.get("dependencies", [])
            if req.get("id") in deps:
                issues.append({
                    "type": "circular_dependency",
                    "requirement": req.get("id"),
                    "severity": "critical"
                })
        
        return {
            "issues": issues,
            "suggestions": suggestions,
            "completeness_score": max(0, 100 - len(issues) * 10),
            "analyzed_count": len(requirements_data)
        }
    
    async def _generate_srs(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generar especificación de requisitos de software."""
        project_name = input_data.get("project_name", "Nuevo Proyecto")
        requirements_data = input_data.get("requirements", [])
        
        # Convertir a objetos Requirement
        requirements = []
        for req_data in requirements_data:
            requirements.append(Requirement(
                id=req_data.get("id", str(uuid.uuid4())),
                title=req_data.get("title", ""),
                description=req_data.get("description", ""),
                type=req_data.get("type", "functional"),
                priority=req_data.get("priority", "medium"),
                source=req_data.get("source", "user"),
                acceptance_criteria=req_data.get("acceptance_criteria", []),
                dependencies=req_data.get("dependencies", [])
            ))
        
        srs = SoftwareRequirementsSpec(
            id=str(uuid.uuid4()),
            project_name=project_name,
            version="1.0.0",
            requirements=requirements,
            use_cases=[],
            glossary={
                "API": "Application Programming Interface",
                "CRUD": "Create, Read, Update, Delete",
                "SRS": "Software Requirements Specification"
            },
            assumptions=["Recursos suficientes para desarrollo"],
            constraints=["Presupuesto limitado", "Timeline de 3 meses"]
        )
        
        self._current_srs = srs
        self._requirement_store[srs.id] = srs
        
        return {
            "srs_id": srs.id,
            "project_name": srs.project_name,
            "version": srs.version,
            "requirements_count": len(srs.requirements),
            "glossary": srs.glossary,
            "assumptions": srs.assumptions,
            "constraints": srs.constraints
        }
    
    async def _create_use_cases(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Crear casos de uso desde requisitos."""
        requirements_data = input_data.get("requirements", [])
        
        use_cases = []
        
        for req in requirements_data:
            if req.get("type") == "functional":
                uc = UseCase(
                    id=str(uuid.uuid4()),
                    name=f"UC-{req.get('title', 'Unknown').replace(' ', '_')}",
                    actor="Usuario",
                    description=req.get("description", ""),
                    preconditions=["Usuario autenticado"],
                    steps=[
                        f"1. Usuario inicia acción: {req.get('title')}",
                        "2. Sistema procesa solicitud",
                        "3. Sistema retorna resultado"
                    ],
                    postconditions=["Operación completada", "Datos actualizados"]
                )
                use_cases.append(uc)
        
        return {
            "use_cases": [self._use_case_to_dict(uc) for uc in use_cases],
            "count": len(use_cases)
        }
    
    async def _validate_requirements(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validar requisitos contra estándares."""
        requirements_data = input_data.get("requirements", [])
        
        validation_results = []
        
        for req in requirements_data:
            issues = []
            
            # Verificar formato de ID
            if not req.get("id"):
                issues.append("Missing ID")
            
            # Verificar descripción
            if len(req.get("description", "")) < 20:
                issues.append("Description too short")
            
            # Verificar criterios de aceptación
            if not req.get("acceptance_criteria"):
                issues.append("No acceptance criteria")
            elif len(req.get("acceptance_criteria", [])) < 2:
                issues.append("Insufficient acceptance criteria")
            
            validation_results.append({
                "requirement_id": req.get("id"),
                "valid": len(issues) == 0,
                "issues": issues
            })
        
        valid_count = sum(1 for r in validation_results if r["valid"])
        
        return {
            "validation_results": validation_results,
            "total": len(validation_results),
            "valid": valid_count,
            "invalid": len(validation_results) - valid_count,
            "validation_rate": valid_count / len(validation_results) if validation_results else 0
        }
    
    async def shutdown(self) -> None:
        """Limpiar recursos."""
        self.update_state(AgentState.SHUTTING_DOWN)
        logger.info(f"Shutting down {self._name}")
        self.update_state(AgentState.IDLE)
    
    def _requirement_to_dict(self, req: Requirement) -> Dict[str, Any]:
        """Convertir requisito a diccionario."""
        return {
            "id": req.id,
            "title": req.title,
            "description": req.description,
            "type": req.type,
            "priority": req.priority,
            "source": req.source,
            "acceptance_criteria": req.acceptance_criteria,
            "dependencies": req.dependencies,
            "status": req.status,
            "created_at": req.created_at.isoformat(),
            "updated_at": req.updated_at.isoformat()
        }
    
    def _use_case_to_dict(self, uc: UseCase) -> Dict[str, Any]:
        """Convertir caso de uso a diccionario."""
        return {
            "id": uc.id,
            "name": uc.name,
            "actor": uc.actor,
            "description": uc.description,
            "preconditions": uc.preconditions,
            "steps": uc.steps,
            "postconditions": uc.postconditions,
            "alternative_flows": uc.alternative_flows
        }
    
    def get_current_srs(self) -> Optional[SoftwareRequirementsSpec]:
        """Obtener SRS actual."""
        return self._current_srs
    
    def get_requirement_store(self) -> Dict[str, SoftwareRequirementsSpec]:
        """Obtener store de requisitos."""
        return self._requirement_store