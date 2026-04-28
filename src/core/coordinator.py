"""Coordinator for orchestrating multi-agent workflows."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

from src.agents.base.base_agent import BaseAgent, Task, TaskResult, TaskStatus
from src.agents.base.agent_protocol import AgentMessage, MessageType, Priority

logger = logging.getLogger(__name__)


class WorkflowStatus(Enum):
    """Estados del workflow."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowStage(Enum):
    """Etapas del workflow de desarrollo."""
    REQUIREMENTS = "requirements"
    DESIGN = "design"
    CODE_BACKEND = "code_backend"
    CODE_FRONTEND = "code_frontend"
    TESTS = "tests"
    DEPLOY = "deploy"
    MAINTENANCE = "maintenance"


@dataclass
class Workflow:
    """Workflow completo."""
    id: str
    name: str
    status: WorkflowStatus
    current_stage: WorkflowStage
    stages_completed: List[WorkflowStage] = field(default_factory=list)
    tasks: Dict[str, TaskResult] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowDefinition:
    """Definición de un workflow."""
    name: str
    description: str
    stages: List[WorkflowStage]
    agent_mapping: Dict[WorkflowStage, str]
    dependencies: Dict[WorkflowStage, List[WorkflowStage]] = field(default_factory=dict)


class Coordinator:
    """Coordinador central para orquestar agentes."""
    
    # Workflows predefinidos
    DEFAULT_WORKFLOW = WorkflowDefinition(
        name="full_development_cycle",
        description="Ciclo completo de desarrollo de software",
        stages=[
            WorkflowStage.REQUIREMENTS,
            WorkflowStage.DESIGN,
            WorkflowStage.CODE_BACKEND,
            WorkflowStage.CODE_FRONTEND,
            WorkflowStage.TESTS,
            WorkflowStage.DEPLOY,
            WorkflowStage.MAINTENANCE
        ],
        agent_mapping={
            WorkflowStage.REQUIREMENTS: "requirements",
            WorkflowStage.DESIGN: "design",
            WorkflowStage.CODE_BACKEND: "code_backend",
            WorkflowStage.CODE_FRONTEND: "code_frontend",
            WorkflowStage.TESTS: "tests",
            WorkflowStage.DEPLOY: "deploy",
            WorkflowStage.MAINTENANCE: "maintenance"
        },
        dependencies={
            WorkflowStage.DESIGN: [WorkflowStage.REQUIREMENTS],
            WorkflowStage.CODE_BACKEND: [WorkflowStage.DESIGN],
            WorkflowStage.CODE_FRONTEND: [WorkflowStage.CODE_BACKEND],
            WorkflowStage.TESTS: [WorkflowStage.CODE_BACKEND, WorkflowStage.CODE_FRONTEND],
            WorkflowStage.DEPLOY: [WorkflowStage.TESTS],
            WorkflowStage.MAINTENANCE: [WorkflowStage.DEPLOY]
        }
    )
    
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._workflows: Dict[str, Workflow] = {}
        self._workflow_definitions: Dict[str, WorkflowDefinition] = {
            "full_development_cycle": self.DEFAULT_WORKFLOW
        }
        self._message_broker = None
        self._event_bus = None
    
    def register_agent(self, agent: BaseAgent) -> None:
        """Registrar un agente."""
        self._agents[agent.agent_id] = agent
        logger.info(f"Registered agent: {agent.agent_id}")
    
    def unregister_agent(self, agent_id: str) -> None:
        """Desregistrar un agente."""
        if agent_id in self._agents:
            del self._agents[agent_id]
            logger.info(f"Unregistered agent: {agent_id}")
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Obtener un agente por ID."""
        return self._agents.get(agent_id)
    
    def list_agents(self) -> List[str]:
        """Listar todos los agentes registrados."""
        return list(self._agents.keys())
    
    async def initialize_all(self) -> None:
        """Inicializar todos los agentes."""
        for agent in self._agents.values():
            await agent.initialize()
        logger.info(f"Initialized {len(self._agents)} agents")
    
    async def shutdown_all(self) -> None:
        """Apagar todos los agentes."""
        for agent in self._agents.values():
            await agent.shutdown()
        logger.info(f"Shut down {len(self._agents)} agents")
    
    async def submit_task(self, task: Task, agent_id: Optional[str] = None) -> TaskResult:
        """Enviar una tarea a un agente específico."""
        target_agent_id = agent_id or task.metadata.get("agent_id")
        
        if not target_agent_id:
            raise ValueError("No agent specified for task")
        
        agent = self._agents.get(target_agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {target_agent_id}")
        
        return await agent.execute(task)
    
    async def create_workflow(
        self,
        workflow_name: str,
        input_data: Dict[str, Any]
    ) -> str:
        """Crear un nuevo workflow."""
        workflow_def = self._workflow_definitions.get(workflow_name)
        if not workflow_def:
            raise ValueError(f"Unknown workflow: {workflow_name}")
        
        workflow = Workflow(
            id=str(uuid.uuid4()),
            name=workflow_def.name,
            status=WorkflowStatus.PENDING,
            current_stage=workflow_def.stages[0],
            metadata=input_data
        )
        
        self._workflows[workflow.id] = workflow
        logger.info(f"Created workflow: {workflow.id}")
        
        return workflow.id
    
    async def execute_workflow(self, workflow_id: str) -> Workflow:
        """Ejecutar un workflow completo."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        workflow_def = self._workflow_definitions.get(workflow.name)
        if not workflow_def:
            raise ValueError(f"Workflow definition not found: {workflow.name}")
        
        workflow.status = WorkflowStatus.RUNNING
        
        try:
            for stage in workflow_def.stages:
                workflow.current_stage = stage
                
                # Verificar dependencias
                dependencies = workflow_def.dependencies.get(stage, [])
                for dep in dependencies:
                    if dep not in workflow.stages_completed:
                        raise ValueError(f"Dependency not met: {dep}")
                
                # Obtener agente para esta etapa
                agent_id = workflow_def.agent_mapping.get(stage)
                if not agent_id:
                    raise ValueError(f"No agent mapping for stage: {stage}")
                
                agent = self._agents.get(agent_id)
                if not agent:
                    raise ValueError(f"Agent not found for stage: {agent_id}")
                
                # Crear tarea para el agente
                task = Task(
                    id=str(uuid.uuid4()),
                    type=self._get_task_type_for_stage(stage),
                    input_data=workflow.metadata,
                    metadata={"stage": stage.value}
                )
                
                # Ejecutar tarea
                result = await agent.execute(task)
                workflow.tasks[stage.value] = result
                
                if result.status == TaskStatus.FAILED:
                    workflow.status = WorkflowStatus.FAILED
                    break
                
                workflow.stages_completed.append(stage)
            
            if workflow.status != WorkflowStatus.FAILED:
                workflow.status = WorkflowStatus.COMPLETED
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            workflow.status = WorkflowStatus.FAILED
        
        workflow.updated_at = datetime.now()
        
        return workflow
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[Workflow]:
        """Consultar estado de un workflow."""
        return self._workflows.get(workflow_id)
    
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancelar un workflow en progreso."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return False
        
        if workflow.status == WorkflowStatus.RUNNING:
            workflow.status = WorkflowStatus.CANCELLED
            return True
        
        return False
    
    def _get_task_type_for_stage(self, stage: WorkflowStage) -> str:
        """Obtener el tipo de tarea para una etapa."""
        mapping = {
            WorkflowStage.REQUIREMENTS: "generate_srs",
            WorkflowStage.DESIGN: "create_architecture",
            WorkflowStage.CODE_BACKEND: "generate_code",
            WorkflowStage.CODE_FRONTEND: "generate_components",
            WorkflowStage.TESTS: "generate_tests",
            WorkflowStage.DEPLOY: "create_pipeline",
            WorkflowStage.MAINTENANCE: "monitor_health"
        }
        return mapping.get(stage, "unknown")
    
    def register_workflow_definition(self, definition: WorkflowDefinition) -> None:
        """Registrar una nueva definición de workflow."""
        self._workflow_definitions[definition.name] = definition
    
    def get_workflow_definitions(self) -> List[str]:
        """Obtener lista de definiciones de workflow."""
        return list(self._workflow_definitions.keys())