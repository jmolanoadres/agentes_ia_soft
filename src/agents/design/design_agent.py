"""Design agent for system architecture and design."""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.agents.base.base_agent import (
    AgentState,
    BaseAgent,
    Capability,
    Task,
    TaskResult,
    TaskStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class Component:
    """Componente del sistema."""

    id: str
    name: str
    description: str
    responsibilities: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    interfaces: list[str] = field(default_factory=list)
    technology: str | None = None


@dataclass
class Architecture:
    """Arquitectura del sistema."""

    id: str
    name: str
    style: str  # monolithic, microservices, layered, etc.
    components: list[Component] = field(default_factory=list)
    data_flow: list[str] = field(default_factory=list)
    security_model: str | None = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class DesignPattern:
    """Patrón de diseño aplicado."""

    name: str
    description: str
    use_case: str
    components_involved: list[str] = field(default_factory=list)


class DesignAgent(BaseAgent):
    """Agente especializado en diseño de sistemas."""

    def __init__(self) -> None:
        super().__init__(
            agent_id="design",
            name="Design Agent",
            description="Agente para diseño de arquitectura y componentes del sistema",
        )
        self._current_architecture: Architecture | None = None
        self._design_store: dict[str, Architecture] = {}

        self._register_capabilities()

    def _register_capabilities(self) -> None:
        """Registrar las capacidades del agente."""
        self.add_capability(
            Capability(
                name="create_architecture",
                description="Crear arquitectura del sistema",
                version="1.0.0",
            )
        )
        self.add_capability(
            Capability(
                name="design_components",
                description="Diseñar componentes del sistema",
                version="1.0.0",
            )
        )
        self.add_capability(
            Capability(
                name="select_patterns",
                description="Seleccionar patrones de diseño apropiados",
                version="1.0.0",
            )
        )
        self.add_capability(
            Capability(
                name="validate_design",
                description="Validar diseño contra requisitos",
                version="1.0.0",
            )
        )
        self.add_capability(
            Capability(
                name="generate_diagrams",
                description="Generar diagramas de arquitectura",
                version="1.0.0",
            )
        )

    async def initialize(self) -> None:
        """Inicializar el agente."""
        self.update_state(AgentState.INITIALIZING)
        logger.info(f"Initializing {self._name}")
        self.update_state(AgentState.IDLE)

    async def execute(self, task: Task) -> TaskResult:
        """Ejecutar una tarea de diseño."""
        start_time = datetime.now()
        self.update_state(AgentState.PROCESSING)

        try:
            task_type = task.type

            if task_type == "create_architecture":
                result = await self._create_architecture(task.input_data)
            elif task_type == "design_components":
                result = await self._design_components(task.input_data)
            elif task_type == "select_patterns":
                result = await self._select_patterns(task.input_data)
            elif task_type == "validate_design":
                result = await self._validate_design(task.input_data)
            elif task_type == "generate_diagrams":
                result = await self._generate_diagrams(task.input_data)
            else:
                raise ValueError(f"Unknown task type: {task_type}")

            execution_time = (datetime.now() - start_time).total_seconds()
            self.update_metrics(execution_time, success=True)
            self.update_state(AgentState.IDLE)

            return TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                output_data=result,
                execution_time=execution_time,
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
                execution_time=execution_time,
            )

    async def _create_architecture(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Crear arquitectura del sistema."""
        project_name = input_data.get("project_name", "Nuevo Proyecto")
        requirements = input_data.get("requirements", [])

        # Determinar estilo de arquitectura
        if len(requirements) > 20:
            style = "microservices"
        else:
            style = "layered"

        # Crear componentes base
        components = []

        # Capa de presentación
        components.append(
            Component(
                id=str(uuid.uuid4()),
                name="Presentation Layer",
                description="Capa de interfaz de usuario",
                responsibilities=["Renderizar UI", "Manejar interacciones del usuario"],
                dependencies=[],
                interfaces=["API REST", "GraphQL"],
                technology="FastAPI/React",
            )
        )

        # Capa de negocio
        components.append(
            Component(
                id=str(uuid.uuid4()),
                name="Business Layer",
                description="Capa de lógica de negocio",
                responsibilities=["Ejecutar reglas de negocio", "Orquestar procesos"],
                dependencies=["Presentation Layer"],
                interfaces=["Servicios de dominio"],
                technology="Python",
            )
        )

        # Capa de datos
        components.append(
            Component(
                id=str(uuid.uuid4()),
                name="Data Layer",
                description="Capa de acceso a datos",
                responsibilities=["Persistencia de datos", "Consultas"],
                dependencies=["Business Layer"],
                interfaces=["Repository pattern"],
                technology="SQLAlchemy/PostgreSQL",
            )
        )

        architecture = Architecture(
            id=str(uuid.uuid4()),
            name=f"{project_name} Architecture",
            style=style,
            components=components,
            data_flow=["UI → API → Services → Repository → Database"],
            security_model="JWT Authentication",
        )

        self._current_architecture = architecture
        self._design_store[architecture.id] = architecture

        return {
            "architecture_id": architecture.id,
            "name": architecture.name,
            "style": architecture.style,
            "components": [self._component_to_dict(c) for c in architecture.components],
            "data_flow": architecture.data_flow,
            "security_model": architecture.security_model,
        }

    async def _design_components(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Diseñar componentes específicos."""
        component_specs = input_data.get("components", [])

        components = []

        for spec in component_specs:
            component = Component(
                id=str(uuid.uuid4()),
                name=spec.get("name", ""),
                description=spec.get("description", ""),
                responsibilities=spec.get("responsibilities", []),
                dependencies=spec.get("dependencies", []),
                interfaces=spec.get("interfaces", []),
                technology=spec.get("technology"),
            )
            components.append(component)

        return {
            "components": [self._component_to_dict(c) for c in components],
            "count": len(components),
        }

    async def _select_patterns(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Seleccionar patrones de diseño apropiados."""
        requirements = input_data.get("requirements", [])

        patterns = []

        # Analizar requisitos y sugerir patrones
        for req in requirements:
            req_title = req.get("title", "").lower()

            if "api" in req_title or "rest" in req_title:
                patterns.append(
                    DesignPattern(
                        name="Repository Pattern",
                        description="Abstrae el acceso a datos",
                        use_case="Acceso a API REST",
                        components_involved=["Data Layer", "Business Layer"],
                    )
                )

            if "autenticación" in req_title or "auth" in req_title:
                patterns.append(
                    DesignPattern(
                        name="Strategy Pattern",
                        description="Permite múltiples métodos de autenticación",
                        use_case="Autenticación flexible",
                        components_involved=["Business Layer", "Presentation Layer"],
                    )
                )

            if "cache" in req_title:
                patterns.append(
                    DesignPattern(
                        name="Cache-Aside",
                        description="Estrategia de caché",
                        use_case="Optimización de rendimiento",
                        components_involved=["Data Layer"],
                    )
                )

        # Deduplicar patrones
        unique_patterns = []
        seen = set()
        for p in patterns:
            if p.name not in seen:
                unique_patterns.append(p)
                seen.add(p.name)

        return {
            "patterns": [self._pattern_to_dict(p) for p in unique_patterns],
            "count": len(unique_patterns),
        }

    async def _validate_design(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Validar diseño contra requisitos."""
        architecture_data = input_data.get("architecture", {})
        requirements = input_data.get("requirements", [])

        issues: list[dict[str, Any]] = []
        coverage: list[dict[str, Any]] = []

        # Verificar que los componentes cubran los requisitos
        for req in requirements:
            req_type = req.get("type", "")
            covered = False

            for component in architecture_data.get("components", []):
                if req_type == "functional":
                    covered = True
                elif req_type == "non_functional":
                    # Verificar componentes de infraestructura
                    if "Data Layer" in component.get("name", ""):
                        covered = True

            coverage.append({"requirement_id": req.get("id"), "covered": covered})

        covered_count = sum(1 for c in coverage if c["covered"])

        return {
            "coverage": coverage,
            "coverage_rate": covered_count / len(requirements) if requirements else 0,
            "issues": issues,
        }

    async def _generate_diagrams(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Generar diagramas de arquitectura."""
        architecture_data = input_data.get("architecture", {})

        # Generar descripción de diagrama en formato texto
        diagram_description = """
# Diagrama de Arquitectura

```mermaid
graph TD
    UI[UI Layer] --> API[API Gateway]
    API --> SVC[Business Services]
    SVC --> REPO[Repository]
    REPO --> DB[(Database)]
    SVC --> CACHE[Cache]
    SVC --> QUEUE[Message Queue]
```

## Componentes:
"""
        for comp in architecture_data.get("components", []):
            diagram_description += f"\n### {comp.get('name', 'Unknown')}\n"
            diagram_description += f"- {comp.get('description', '')}\n"

        return {
            "diagram": diagram_description,
            "format": "mermaid",
            "components_count": len(architecture_data.get("components", [])),
        }

    async def shutdown(self) -> None:
        """Limpiar recursos."""
        self.update_state(AgentState.SHUTTING_DOWN)
        logger.info(f"Shutting down {self._name}")
        self.update_state(AgentState.IDLE)

    def _component_to_dict(self, comp: Component) -> dict[str, Any]:
        """Convertir componente a diccionario."""
        return {
            "id": comp.id,
            "name": comp.name,
            "description": comp.description,
            "responsibilities": comp.responsibilities,
            "dependencies": comp.dependencies,
            "interfaces": comp.interfaces,
            "technology": comp.technology,
        }

    def _pattern_to_dict(self, pattern: DesignPattern) -> dict[str, Any]:
        """Convertir patrón a diccionario."""
        return {
            "name": pattern.name,
            "description": pattern.description,
            "use_case": pattern.use_case,
            "components_involved": pattern.components_involved,
        }

    def get_current_architecture(self) -> Architecture | None:
        """Obtener arquitectura actual."""
        return self._current_architecture
