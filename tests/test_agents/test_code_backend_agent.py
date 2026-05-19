"""Tests for Code Backend Agent."""

from typing import Any

import pytest

from src.agents.base.base_agent import Task, TaskStatus
from src.agents.code.code_backend_agent import CodeBackendAgent


@pytest.fixture
def code_backend_agent() -> Any:
    """Create code backend agent instance."""
    return CodeBackendAgent()


@pytest.mark.asyncio
async def test_initialization(code_backend_agent: Any) -> None:
    """Test agent initialization."""
    await code_backend_agent.initialize()

    assert code_backend_agent.state.value == "idle"
    assert len(code_backend_agent.capabilities) > 0


@pytest.mark.asyncio
async def test_generate_code(code_backend_agent: Any) -> None:
    """Test code generation."""
    await code_backend_agent.initialize()

    task = Task(
        id="test-1",
        type="generate_code",
        input_data={
            "entity_name": "User",
            "framework": "fastapi",
            "modules": ["model", "schema", "service", "route"],
        },
    )

    result = await code_backend_agent.execute(task)

    assert result.status == TaskStatus.COMPLETED
    assert "modules" in result.output_data
    assert result.output_data["count"] == 4


@pytest.mark.asyncio
async def test_refactor_code(code_backend_agent: Any) -> None:
    """Test code refactoring."""
    await code_backend_agent.initialize()

    task = Task(
        id="test-2",
        type="refactor_code",
        input_data={
            "code": "def old_function():\n    pass",
            "refactor_type": "rename",
            "old_name": "old_function",
            "new_name": "new_function",
        },
    )

    result = await code_backend_agent.execute(task)

    assert result.status == TaskStatus.COMPLETED
    assert "refactored_code" in result.output_data


@pytest.mark.asyncio
async def test_apply_standards(code_backend_agent: Any) -> None:
    """Test standards application."""
    await code_backend_agent.initialize()

    task = Task(id="test-3", type="apply_standards", input_data={"code": "def test():\n    pass"})

    result = await code_backend_agent.execute(task)

    assert result.status == TaskStatus.COMPLETED
    assert "issues" in result.output_data


@pytest.mark.asyncio
async def test_manage_dependencies(code_backend_agent: Any) -> None:
    """Test dependency management."""
    await code_backend_agent.initialize()

    task = Task(
        id="test-4",
        type="manage_dependencies",
        input_data={"dependencies": ["fastapi", "pytest"], "new_dependencies": ["uvicorn"]},
    )

    result = await code_backend_agent.execute(task)

    assert result.status == TaskStatus.COMPLETED
    assert "all_dependencies" in result.output_data


@pytest.mark.asyncio
async def test_shutdown(code_backend_agent: Any) -> None:
    """Test agent shutdown."""
    await code_backend_agent.initialize()
    await code_backend_agent.shutdown()

    assert code_backend_agent.state.value == "idle"
