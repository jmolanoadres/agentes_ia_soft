# SDLAS - Software Development Lifecycle Agent System

Sistema multiagente autónomo para automatización completa del ciclo de vida del desarrollo de software.

## Características

- **6 Agentes Especializados**: Requirements, Design, Code, Tests, Deploy, Maintenance
- **Orquestación Central**: Coordinator para gestión de workflows
- **Comunicación Interagentes**: Message Broker y Event Bus
- **Métricas en Tiempo Real**: Collector para monitoreo del sistema
- **Arquitectura Extensible**: Sistema de plugins para nuevos agentes

## Requisitos

- Python 3.11+
- uv (gestor de paquetes)

## Instalación

```bash
# Instalar dependencias
uv sync

# Instalar dev dependencies
uv sync --extra dev
```

## Uso Básico

```python
import asyncio
from src.core.coordinator import Coordinator
from src.agents.requirements.requirements_agent import RequirementsAgent
from src.agents.design.design_agent import DesignAgent
from src.agents.code.code_backend_agent import CodeBackendAgent
from src.agents.code.code_frontend_agent import CodeFrontendAgent
from src.agents.tests.tests_agent import TestsAgent
from src.agents.deploy.deploy_agent import DeployAgent
from src.agents.maintenance.maintenance_agent import MaintenanceAgent
from src.agents.base.base_agent import Task

async def main():
    # Crear coordinator
    coordinator = Coordinator()
    
    # Registrar agentes
    coordinator.register_agent(RequirementsAgent())
    coordinator.register_agent(DesignAgent())
    coordinator.register_agent(CodeBackendAgent())
    coordinator.register_agent(CodeFrontendAgent())
    coordinator.register_agent(TestsAgent())
    coordinator.register_agent(DeployAgent())
    coordinator.register_agent(MaintenanceAgent())
    
    # Inicializar todos los agentes
    await coordinator.initialize_all()
    
    # Crear workflow
    workflow_id = await coordinator.create_workflow(
        "full_development_cycle",
        {"project_name": "Mi Proyecto"}
    )
    
    # Ejecutar workflow
    workflow = await coordinator.execute_workflow(workflow_id)
    
    print(f"Workflow status: {workflow.status.value}")
    
    # Apagar agentes
    await coordinator.shutdown_all()

asyncio.run(main())
```

## Estructura del Proyecto

```
src/
├── agents/
│   ├── base/          # Clases base y protocolos
│   ├── requirements/  # Agente de requisitos
│   ├── design/        # Agente de diseño
│   ├── code/          # Agente de código
│   ├── tests/         # Agente de pruebas
│   ├── deploy/        # Agente de despliegue
│   └── maintenance/   # Agente de mantenimiento
├── core/
│   ├── coordinator.py     # Orquestador central
│   ├── message_broker.py  # Broker de mensajes
│   ├── event_bus.py       # Bus de eventos
│   └── metrics.py         # Recolector de métricas
└── utils/
    ├── config.py      # Configuración
    ├── logging.py    # Logging
    └── helpers.py    # Utilidades
```

## Configuración

Ver [config/settings.yaml](config/settings.yaml) para configuración global.

## Testing

```bash
# Ejecutar todos los tests
uv run pytest

# Ejecutar con coverage
uv run pytest --cov=src
```

## Documentación

- [SPEC.md](SPEC.md) - Especificación completa del sistema
- [docs/](docs/) - Documentación adicional

## Licencia

MIT