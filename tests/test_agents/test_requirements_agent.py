"""Tests for Requirements Agent."""

from typing import Any

import pytest

from src.agents.base.base_agent import Task, TaskStatus
from src.agents.requirements import (
    ApprovalGate,
    ApprovalStatus,
    DesignHandoffPackage,
    PriorityLevel,
    Requirement,
    RequirementsAgentV2,
    RequirementType,
    SoftwareRequirementsSpec,
    SRSVersion,
    UseCase,
)


@pytest.fixture
def requirements_agent() -> Any:
    """Create requirements agent instance."""
    return RequirementsAgentV2()


@pytest.mark.asyncio
async def test_initialization(requirements_agent: Any) -> None:
    """Test agent initialization."""
    await requirements_agent.initialize()

    assert requirements_agent.state.value == "idle"
    assert len(requirements_agent.capabilities) > 0


@pytest.mark.asyncio
async def test_gather_requirements(requirements_agent: Any) -> None:
    """Test requirements gathering."""
    await requirements_agent.initialize()

    task = Task(
        id="test-1", type="gather_requirements", input_data={"project_description": "Test project"}
    )

    result = await requirements_agent.execute(task)

    assert result.status == TaskStatus.COMPLETED
    assert "requirements" in result.output_data
    assert result.output_data["count"] > 0


@pytest.mark.asyncio
async def test_generate_srs(requirements_agent: Any) -> None:
    """Test SRS generation."""
    await requirements_agent.initialize()

    task = Task(
        id="test-2",
        type="generate_srs",
        input_data={
            "project_name": "Test Project",
            "requirements": [
                {
                    "id": "req-1",
                    "title": "Test Requirement",
                    "description": "Test description",
                    "type": "functional",
                    "priority": "high",
                    "source": "user",
                }
            ],
        },
    )

    result = await requirements_agent.execute(task)

    assert result.status == TaskStatus.COMPLETED
    assert "srs_id" in result.output_data
    assert result.output_data["project_name"] == "Test Project"


@pytest.mark.asyncio
async def test_run_full_pipeline(requirements_agent: Any) -> None:
    await requirements_agent.initialize()

    task = Task(
        id="test-2b",
        type="run_full_pipeline",
        input_data={
            "project_name": "Test Project",
            "project_description": "Crear una API REST para gestionar usuarios con autenticación, roles y auditoría.",
        },
    )

    result = await requirements_agent.execute(task)

    assert result.status == TaskStatus.COMPLETED
    assert result.output_data["project_name"] == "Test Project"
    assert "srs" in result.output_data
    assert result.output_data["requirements_count"] >= 0


@pytest.mark.asyncio
async def test_detect_conflicts(requirements_agent: Any) -> None:
    await requirements_agent.initialize()

    task = Task(
        id="test-2c",
        type="detect_conflicts",
        input_data={
            "requirements": [
                {
                    "id": "req-1",
                    "title": "Login de usuario",
                    "description": "El usuario debe iniciar sesión.",
                    "type": "functional",
                    "priority": "must",
                },
                {
                    "id": "req-1",
                    "title": "Login de usuario",
                    "description": "El usuario debe iniciar sesión con OTP.",
                    "type": "security",
                    "priority": "critical",
                },
            ]
        },
    )

    result = await requirements_agent.execute(task)

    assert result.status == TaskStatus.COMPLETED
    assert result.output_data["conflict_count"] >= 1
    assert any(issue["type"] == "duplicate_id" for issue in result.output_data["conflicts"])


@pytest.mark.asyncio
async def test_validate_requirements(requirements_agent: Any) -> None:
    """Test requirements validation."""
    await requirements_agent.initialize()

    task = Task(
        id="test-3",
        type="validate_requirements",
        input_data={
            "requirements": [
                {
                    "id": "req-1",
                    "title": "Test",
                    "description": "Test description",
                    "acceptance_criteria": ["Criterion 1", "Criterion 2"],
                }
            ]
        },
    )

    result = await requirements_agent.execute(task)

    assert result.status == TaskStatus.COMPLETED
    assert "validation_results" in result.output_data


@pytest.mark.asyncio
async def test_shutdown(requirements_agent: Any) -> None:
    """Test agent shutdown."""
    await requirements_agent.initialize()
    await requirements_agent.shutdown()

    assert requirements_agent.state.value == "idle"


def test_approval_gate_auto_approval() -> None:
    import asyncio

    srs = SoftwareRequirementsSpec(
        id="SRS-0001",
        project_name="Test Project",
        description="SRS de prueba",
        version="1.0.0",
        current_version=SRSVersion(version="1.0.0", created_by="tester"),
        requirements=[
            Requirement(
                id="req-1",
                title="Requisito de prueba",
                description="El sistema debe permitir el inicio de sesión con credenciales válidas.",
                type=RequirementType.FUNCTIONAL,
                priority=PriorityLevel.MUST,
                source="user",
                acceptance_criteria=[
                    "El usuario ingresa credenciales válidas.",
                    "El sistema autentica al usuario y redirige al dashboard.",
                ],
            )
        ],
        use_cases=[],
        glossary={},
        assumptions=["Usuario registrado disponible"],
        constraints=[],
        approval_status=ApprovalStatus.PENDING,
        completeness_score=100.0,
        ambiguity_score=0.0,
    )
    gate = ApprovalGate(timeout_seconds=1)

    async def run_gate() -> tuple[Any, Any]:
        request = await gate.request_approval(srs, None)
        response = await gate.wait_for_response(request.id)
        return request, response

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        request, response = loop.run_until_complete(run_gate())
    finally:
        loop.close()

    assert request.request_id == response.request_id
    assert response.status == ApprovalStatus.APPROVED
    assert response.reviewed_by == "auto_approval_system"


def test_design_handoff_package_created() -> None:
    from src.agents.requirements import ApprovalResponse
    from src.agents.requirements.requirements_flow import DesignHandoff

    requirement = Requirement(
        id="req-1",
        title="Requisito de prueba",
        description="El sistema debe notificar al usuario.",
        type=RequirementType.FUNCTIONAL,
        priority=PriorityLevel.HIGH,
        source="user",
    )
    use_case = UseCase(
        id="UC-1",
        name="UC-Prueba",
        actor="Usuario",
        description="El usuario recibe una notificación.",
        related_requirements=[requirement.id],
        preconditions=["El usuario está registrado"],
        steps=["1. Solicitar notificación", "2. Mostrar notificación"],
        postconditions=["Notificación entregada"],
    )
    srs = SoftwareRequirementsSpec(
        id="SRS-0001",
        project_name="Test Project",
        description="SRS de prueba",
        version="1.0.0",
        current_version=SRSVersion(version="1.0.0", created_by="tester"),
        requirements=[requirement],
        use_cases=[use_case],
        glossary={},
        assumptions=[],
        constraints=[],
        approval_status=ApprovalStatus.APPROVED,
    )

    package = DesignHandoff.create_package(
        srs,
        ApprovalResponse(
            request_id="req-approval",
            status=ApprovalStatus.APPROVED,
            reviewed_by="tester",
            comments="Aprobado",
        ),
    )

    assert isinstance(package, DesignHandoffPackage)
    assert package.srs_id == srs.id
    assert package.approval_response is not None
    assert package.traceability_matrix is not None
    assert package.traceability_matrix.srs_id == srs.id
