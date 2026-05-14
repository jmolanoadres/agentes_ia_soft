"""Tests for Requirements Agent."""

import pytest
from src.agents.requirements import RequirementsAgentV2
from src.agents.base.base_agent import Task, TaskStatus


@pytest.fixture
def requirements_agent():
    """Create requirements agent instance."""
    return RequirementsAgentV2()


@pytest.mark.asyncio
async def test_initialization(requirements_agent):
    """Test agent initialization."""
    await requirements_agent.initialize()
    
    assert requirements_agent.state.value == "idle"
    assert len(requirements_agent.capabilities) > 0


@pytest.mark.asyncio
async def test_gather_requirements(requirements_agent):
    """Test requirements gathering."""
    await requirements_agent.initialize()
    
    task = Task(
        id="test-1",
        type="gather_requirements",
        input_data={"project_description": "Test project"}
    )
    
    result = await requirements_agent.execute(task)
    
    assert result.status == TaskStatus.COMPLETED
    assert "requirements" in result.output_data
    assert result.output_data["count"] > 0


@pytest.mark.asyncio
async def test_generate_srs(requirements_agent):
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
                    "source": "user"
                }
            ]
        }
    )
    
    result = await requirements_agent.execute(task)
    
    assert result.status == TaskStatus.COMPLETED
    assert "srs_id" in result.output_data
    assert result.output_data["project_name"] == "Test Project"


@pytest.mark.asyncio
async def test_run_full_pipeline(requirements_agent):
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
async def test_detect_conflicts(requirements_agent):
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
async def test_validate_requirements(requirements_agent):
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
                    "acceptance_criteria": ["Criterion 1", "Criterion 2"]
                }
            ]
        }
    )
    
    result = await requirements_agent.execute(task)
    
    assert result.status == TaskStatus.COMPLETED
    assert "validation_results" in result.output_data


@pytest.mark.asyncio
async def test_shutdown(requirements_agent):
    """Test agent shutdown."""
    await requirements_agent.initialize()
    await requirements_agent.shutdown()
    
    assert requirements_agent.state.value == "idle"