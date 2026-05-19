"""Tests for Design Agent."""

from typing import Any

import pytest

from src.agents.base.base_agent import Task, TaskStatus
from src.agents.design.design_agent import DesignAgent


@pytest.fixture
def design_agent() -> Any:
    """Create design agent instance."""
    return DesignAgent()


@pytest.mark.asyncio
async def test_initialization(design_agent: Any) -> None:
    """Test agent initialization."""
    await design_agent.initialize()

    assert design_agent.state.value == "idle"
    assert len(design_agent.capabilities) > 0


@pytest.mark.asyncio
async def test_create_architecture(design_agent: Any) -> None:
    """Test architecture creation."""
    await design_agent.initialize()

    task = Task(
        id="test-1",
        type="create_architecture",
        input_data={
            "project_name": "Test Project",
            "requirements": [{"id": "req-1", "type": "functional", "title": "Feature 1"}],
        },
    )

    result = await design_agent.execute(task)

    assert result.status == TaskStatus.COMPLETED
    assert "architecture_id" in result.output_data
    assert "components" in result.output_data


@pytest.mark.asyncio
async def test_select_patterns(design_agent: Any) -> None:
    """Test design pattern selection."""
    await design_agent.initialize()

    task = Task(
        id="test-2",
        type="select_patterns",
        input_data={
            "requirements": [
                {"id": "req-1", "type": "functional", "title": "API REST"},
                {"id": "req-2", "type": "functional", "title": "Authentication"},
            ]
        },
    )

    result = await design_agent.execute(task)

    assert result.status == TaskStatus.COMPLETED
    assert "patterns" in result.output_data


@pytest.mark.asyncio
async def test_validate_design(design_agent: Any) -> None:
    """Test design validation."""
    await design_agent.initialize()

    task = Task(
        id="test-3",
        type="validate_design",
        input_data={
            "architecture": {"components": [{"name": "Business Layer", "description": "Layer"}]},
            "requirements": [{"id": "req-1", "type": "functional"}],
        },
    )

    result = await design_agent.execute(task)

    assert result.status == TaskStatus.COMPLETED
    assert "coverage_rate" in result.output_data


@pytest.mark.asyncio
async def test_shutdown(design_agent: Any) -> None:
    """Test agent shutdown."""
    await design_agent.initialize()
    await design_agent.shutdown()

    assert design_agent.state.value == "idle"
