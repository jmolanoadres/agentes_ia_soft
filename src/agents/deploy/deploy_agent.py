"""Deploy agent for CI/CD and deployment automation."""

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
class DeploymentConfig:
    """Configuración de despliegue."""

    id: str
    environment: str  # dev, staging, production
    image_tag: str
    replicas: int = 1
    resources: dict[str, Any] = field(default_factory=dict)
    env_vars: dict[str, str] = field(default_factory=dict)


@dataclass
class Pipeline:
    """Pipeline de CI/CD."""

    id: str
    name: str
    stages: list[str] = field(default_factory=list)
    status: str = "pending"
    last_run: datetime | None = None
    duration: float = 0.0


class DeployAgent(BaseAgent):
    """Agente especializado en despliegue y CI/CD."""

    def __init__(self) -> None:
        super().__init__(
            agent_id="deploy",
            name="Deploy Agent",
            description="Agente para automatización de despliegues y pipelines CI/CD",
        )
        self._pipelines: dict[str, Pipeline] = {}
        self._deploy_configs: dict[str, DeploymentConfig] = {}

        self._register_capabilities()

    def _register_capabilities(self) -> None:
        """Registrar las capacidades del agente."""
        self.add_capability(
            Capability(
                name="create_pipeline", description="Crear pipeline de CI/CD", version="1.0.0"
            )
        )
        self.add_capability(
            Capability(
                name="configure_deployment", description="Configurar despliegue", version="1.0.0"
            )
        )
        self.add_capability(
            Capability(
                name="execute_deployment", description="Ejecutar despliegue", version="1.0.0"
            )
        )
        self.add_capability(
            Capability(name="rollback", description="Realizar rollback", version="1.0.0")
        )
        self.add_capability(
            Capability(name="manage_secrets", description="Gestionar secretos", version="1.0.0")
        )

    async def initialize(self) -> None:
        """Inicializar el agente."""
        self.update_state(AgentState.INITIALIZING)
        logger.info(f"Initializing {self._name}")
        self.update_state(AgentState.IDLE)

    async def execute(self, task: Task) -> TaskResult:
        """Ejecutar una tarea de despliegue."""
        start_time = datetime.now()
        self.update_state(AgentState.PROCESSING)

        try:
            task_type = task.type

            if task_type == "create_pipeline":
                result = await self._create_pipeline(task.input_data)
            elif task_type == "configure_deployment":
                result = await self._configure_deployment(task.input_data)
            elif task_type == "execute_deployment":
                result = await self._execute_deployment(task.input_data)
            elif task_type == "rollback":
                result = await self._rollback(task.input_data)
            elif task_type == "manage_secrets":
                result = await self._manage_secrets(task.input_data)
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

    async def _create_pipeline(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Crear pipeline de CI/CD."""
        project_name = input_data.get("project_name", "project")
        stages = input_data.get("stages", ["build", "test", "deploy"])

        pipeline = Pipeline(
            id=str(uuid.uuid4()), name=f"{project_name}-pipeline", stages=stages, status="created"
        )

        self._pipelines[pipeline.id] = pipeline

        # Generar configuración de GitHub Actions
        github_actions_config = self._generate_github_actions(pipeline, stages)

        # Generar Dockerfile
        dockerfile = self._generate_dockerfile(project_name)

        # Generar docker-compose
        docker_compose = self._generate_docker_compose(project_name)

        return {
            "pipeline_id": pipeline.id,
            "pipeline_name": pipeline.name,
            "stages": pipeline.stages,
            "github_actions": github_actions_config,
            "dockerfile": dockerfile,
            "docker_compose": docker_compose,
        }

    async def _configure_deployment(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Configurar despliegue."""
        environment = input_data.get("environment", "dev")
        image_tag = input_data.get("image_tag", "latest")
        replicas = input_data.get("replicas", 1)

        config = DeploymentConfig(
            id=str(uuid.uuid4()),
            environment=environment,
            image_tag=image_tag,
            replicas=replicas,
            resources={"cpu": "500m", "memory": "512Mi"},
            env_vars={"ENV": environment, "LOG_LEVEL": "info"},
        )

        self._deploy_configs[config.id] = config

        return {
            "config_id": config.id,
            "environment": config.environment,
            "image_tag": config.image_tag,
            "replicas": config.replicas,
            "resources": config.resources,
            "env_vars": config.env_vars,
        }

    async def _execute_deployment(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Ejecutar despliegue."""
        environment = input_data.get("environment", "dev")

        # Simular despliegue
        deployment_result = {
            "status": "deployed",
            "environment": environment,
            "url": f"https://{environment}.example.com",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
        }

        return {
            "deployment_id": str(uuid.uuid4()),
            "status": deployment_result["status"],
            "environment": deployment_result["environment"],
            "url": deployment_result["url"],
            "version": deployment_result["version"],
            "deployed_at": deployment_result["timestamp"],
        }

    async def _rollback(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Realizar rollback."""
        target_version = input_data.get("target_version", "previous")

        return {
            "rollback_id": str(uuid.uuid4()),
            "status": "rolled_back",
            "from_version": "current",
            "to_version": target_version,
            "timestamp": datetime.now().isoformat(),
        }

    async def _manage_secrets(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Gestionar secretos."""
        secrets = input_data.get("secrets", [])
        action = input_data.get("action", "list")  # list, add, remove

        managed_secrets = {}

        if action == "list":
            managed_secrets = {"DATABASE_URL": "***", "API_KEY": "***", "SECRET_KEY": "***"}
        elif action == "add":
            for secret in secrets:
                managed_secrets[secret.get("name")] = "***"

        return {"action": action, "secrets": managed_secrets, "count": len(managed_secrets)}

    async def shutdown(self) -> None:
        """Limpiar recursos."""
        self.update_state(AgentState.SHUTTING_DOWN)
        logger.info(f"Shutting down {self._name}")
        self.update_state(AgentState.IDLE)

    def _generate_github_actions(self, pipeline: Pipeline, stages: list[str]) -> str:
        """Generar configuración de GitHub Actions."""

        return """name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install uv
          uv sync
      - name: Run tests
        run: uv run pytest
      - name: Build Docker image
        run: docker build -t ${ secrets.REGISTRY }/app:${ github.sha } .

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to production
        run: |
          echo "Deploying to production..."
"""

    def _generate_dockerfile(self, project_name: str) -> str:
        """Generar Dockerfile."""
        return """FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY src/ ./src/

# Expose port
EXPOSE 8000

# Run application
CMD ["uv", "run", "python", "-m", "src"]
"""

    def _generate_docker_compose(self, project_name: str) -> str:
        """Generar docker-compose.yml."""
        return f"""version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/{project_name}
      - REDIS_URL=redis://cache:6379
    depends_on:
      - db
      - cache
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB={project_name}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  cache:
    image: redis:7
    restart: unless-stopped

volumes:
  postgres_data:
"""

    def get_pipelines(self) -> dict[str, Pipeline]:
        """Obtener pipelines."""
        return self._pipelines

    def get_deploy_configs(self) -> dict[str, DeploymentConfig]:
        """Obtener configuraciones de despliegue."""
        return self._deploy_configs
