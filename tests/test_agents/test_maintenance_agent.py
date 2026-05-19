"""Tests for Maintenance Agent."""

from typing import Any

import pytest

from src.agents.base.base_agent import Task, TaskStatus
from src.agents.maintenance.maintenance_agent import MaintenanceAgent


@pytest.fixture
def maintenance_agent() -> Any:
    """Create maintenance agent instance."""
    return MaintenanceAgent()


@pytest.mark.asyncio
async def test_initialization(maintenance_agent: Any) -> None:
    """Test agent initialization."""
    await maintenance_agent.initialize()

    assert maintenance_agent.state.value == "idle"
    assert len(maintenance_agent.capabilities) > 0


@pytest.mark.asyncio
async def test_monitor_health(maintenance_agent: Any) -> None:
    """Test health monitoring."""
    await maintenance_agent.initialize()

    task = Task(id="test-1", type="monitor_health", input_data={})

    result = await maintenance_agent.execute(task)

    assert result.status == TaskStatus.COMPLETED
    assert "overall_status" in result.output_data
    assert "metrics" in result.output_data


@pytest.mark.asyncio
async def test_detect_issues(maintenance_agent: Any) -> None:
    """Test issue detection."""
    await maintenance_agent.initialize()

    task = Task(
        id="test-2",
        type="detect_issues",
        input_data={"cpu_usage": 85, "memory_usage": 90, "error_rate": 6},
    )

    result = await maintenance_agent.execute(task)

    assert result.status == TaskStatus.COMPLETED
    assert "alerts_detected" in result.output_data


@pytest.mark.asyncio
async def test_analyze_logs(maintenance_agent: Any) -> None:
    """Test log analysis."""
    await maintenance_agent.initialize()

    task = Task(
        id="test-3", type="analyze_logs", input_data={"log_pattern": "error", "time_range": "1h"}
    )

    result = await maintenance_agent.execute(task)

    assert result.status == TaskStatus.COMPLETED
    assert "patterns" in result.output_data


@pytest.mark.asyncio
async def test_suggest_improvements(maintenance_agent: Any) -> None:
    """Test improvement suggestions."""
    await maintenance_agent.initialize()

    task = Task(id="test-4", type="suggest_improvements", input_data={})

    result = await maintenance_agent.execute(task)

    assert result.status == TaskStatus.COMPLETED
    assert "suggestions" in result.output_data


@pytest.mark.asyncio
async def test_shutdown(maintenance_agent: Any) -> None:
    """Test agent shutdown."""
    await maintenance_agent.initialize()
    await maintenance_agent.shutdown()

    assert maintenance_agent.state.value == "idle"
