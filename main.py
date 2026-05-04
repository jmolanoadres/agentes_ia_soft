import asyncio
from src.agents.requirements import RequirementsAgentV2
from src.agents.base.base_agent import Task

async def main():
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
    print(result.output_data)

asyncio.run(main())