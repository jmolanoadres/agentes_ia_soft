"""Base agent abstract class."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AgentState(Enum):
    """Estados posibles de un agente."""

    IDLE = "idle"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PROCESSING = "processing"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"


class TaskStatus(Enum):
    """Estados de una tarea."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Capability:
    """Representa una capacidad del agente."""

    name: str
    description: str
    version: str = "1.0.0"
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    """Representa una tarea a ejecutar."""

    id: str
    type: str
    input_data: dict[str, Any]
    priority: int = 5
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResult:
    """Resultado de una tarea."""

    task_id: str
    status: TaskStatus
    output_data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    execution_time: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentMetrics:
    """Métricas de un agente."""

    agent_id: str
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_execution_time: float = 0.0
    average_execution_time: float = 0.0
    last_execution: datetime | None = None


class BaseAgent(ABC):
    """Clase base abstract para todos los agentes."""

    def __init__(self, agent_id: str, name: str, description: str) -> None:
        self._agent_id = agent_id
        self._name = name
        self._description = description
        self._state = AgentState.IDLE
        self._capabilities: list[Capability] = []
        self._metrics = AgentMetrics(agent_id=agent_id)
        self._config: Any = {}

    @property
    def agent_id(self) -> str:
        """Identificador único del agente."""
        return self._agent_id

    @property
    def name(self) -> str:
        """Nombre del agente."""
        return self._name

    @property
    def description(self) -> str:
        """Descripción del agente."""
        return self._description

    @property
    def state(self) -> AgentState:
        """Estado actual del agente."""
        return self._state

    @property
    def capabilities(self) -> list[Capability]:
        """Capacidades del agente."""
        return self._capabilities

    @property
    def metrics(self) -> AgentMetrics:
        """Métricas del agente."""
        return self._metrics

    def update_state(self, new_state: AgentState) -> None:
        """Actualizar el estado del agente."""
        self._state = new_state

    def add_capability(self, capability: Capability) -> None:
        """Añadir una capacidad al agente."""
        self._capabilities.append(capability)

    def update_metrics(self, execution_time: float, success: bool) -> None:
        """Actualizar métricas del agente."""
        if success:
            self._metrics.tasks_completed += 1
        else:
            self._metrics.tasks_failed += 1

        self._metrics.total_execution_time += execution_time
        self._metrics.last_execution = datetime.now()

        total_tasks = self._metrics.tasks_completed + self._metrics.tasks_failed
        if total_tasks > 0:
            self._metrics.average_execution_time = self._metrics.total_execution_time / total_tasks

    @abstractmethod
    async def initialize(self) -> None:
        """Inicializar el agente."""
        pass

    @abstractmethod
    async def execute(self, task: Task) -> TaskResult:
        """Ejecutar una tarea."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Limpiar recursos."""
        pass

    def configure(self, config: dict[str, Any]) -> None:
        """Configurar el agente."""
        self._config = config

    async def validate_task(self, task: Task) -> bool:
        """Validar si el agente puede procesar la tarea."""
        return task.type in [c.name for c in self._capabilities]

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self._agent_id}, state={self._state.value})"
