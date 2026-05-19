"""Tests for Tests Agent."""

from typing import Any

import pytest

from src.agents.base.base_agent import Task, TaskStatus
from src.agents.tests.tests_agent import TestsAgent


@pytest.fixture
def tests_agent() -> Any:
    """Create tests agent instance."""
    return TestsAgent()


@pytest.mark.asyncio
async def test_initialization(tests_agent: Any) -> None:
    """Test agent initialization."""
    await tests_agent.initialize()

    assert tests_agent.state.value == "idle"
    assert len(tests_agent.capabilities) > 0


@pytest.mark.asyncio
async def test_generate_tests(tests_agent: Any) -> None:
    """Test test generation."""
    await tests_agent.initialize()

    task = Task(
        id="test-1",
        type="generate_tests",
        input_data={
            "code_modules": [{"name": "User", "file_path": "src/user.py"}],
            "test_type": "unit",
        },
    )

    result = await tests_agent.execute(task)

    assert result.status == TaskStatus.COMPLETED
    assert "test_suite_id" in result.output_data
    assert "generated_tests" in result.output_data


@pytest.mark.asyncio
async def test_execute_tests(tests_agent: Any) -> None:
    """Test test execution."""
    await tests_agent.initialize()

    task = Task(id="test-2", type="execute_tests", input_data={"test_suite_id": "test-suite-1"})

    result = await tests_agent.execute(task)

    assert result.status == TaskStatus.COMPLETED
    assert "results" in result.output_data
    assert "pass_rate" in result.output_data


@pytest.mark.asyncio
async def test_analyze_coverage(tests_agent: Any) -> None:
    """Test coverage analysis."""
    await tests_agent.initialize()

    task = Task(
        id="test-3",
        type="analyze_coverage",
        input_data={"source_files": ["src/user.py", "src/auth.py"]},
    )

    result = await tests_agent.execute(task)

    assert result.status == TaskStatus.COMPLETED
    assert "total_coverage" in result.output_data


@pytest.mark.asyncio
async def test_shutdown(tests_agent: Any) -> None:
    """Test agent shutdown."""
    await tests_agent.initialize()
    await tests_agent.shutdown()

    assert tests_agent.state.value == "idle"
