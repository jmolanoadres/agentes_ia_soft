import asyncio
import logging
import sys

from src.agents.base.base_agent import Task
from src.agents.requirements import RequirementsAgentV2

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def main() -> None:
    """Execute full requirements pipeline."""
    try:
        agent = RequirementsAgentV2()
        await agent.initialize()

        # Pipeline completo
        task = Task(
            id="task-001",
            type="run_full_pipeline",
            input_data={
                "project_name": "API Gestión Usuarios ADRES",
                "project_description": (
                    "Crear API REST para gestión de usuarios del SGSSS. "
                    "Debe incluir autenticación OAuth2, CRUD de usuarios, "
                    "gestión de roles y permisos, auditoría de accesos, "
                    "integración con LDAP institucional. "
                    "El sistema debe responder en menos de 500ms "
                    "y soportar 1000 usuarios concurrentes."
                ),
            },
        )

        result = await agent.execute(task)
        logger.info(result.output_data)
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
        sys.exit(0)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        sys.exit(1)
