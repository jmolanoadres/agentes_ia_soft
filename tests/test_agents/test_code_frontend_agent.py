"""Tests for Code Frontend Agent."""

from typing import Any

import pytest

from src.agents.base.base_agent import Task, TaskStatus
from src.agents.code.code_frontend_agent import CodeFrontendAgent


@pytest.fixture
def code_frontend_agent() -> Any:
    """Create code frontend agent instance."""
    return CodeFrontendAgent()


@pytest.mark.asyncio
async def test_initialization(code_frontend_agent: Any) -> None:
    """Test agent initialization."""
    await code_frontend_agent.initialize()

    assert code_frontend_agent.state.value == "idle"
    assert len(code_frontend_agent.capabilities) > 0


@pytest.mark.asyncio
async def test_generate_components(code_frontend_agent: Any) -> None:
    """Test component generation."""
    await code_frontend_agent.initialize()

    task = Task(
        id="test-1",
        type="generate_components",
        input_data={
            "component_name": "UserCard",
            "framework": "react",
            "props": {"name": "string", "email": "string"},
        },
    )

    result = await code_frontend_agent.execute(task)

    assert result.status == TaskStatus.COMPLETED
    assert "files" in result.output_data
    assert result.output_data["framework"] == "react"


@pytest.mark.asyncio
async def test_generate_pages(code_frontend_agent: Any) -> None:
    """Test page generation."""
    await code_frontend_agent.initialize()

    task = Task(
        id="test-2",
        type="generate_pages",
        input_data={"page_name": "UserProfile", "framework": "react", "route_path": "/users/:id"},
    )

    result = await code_frontend_agent.execute(task)

    assert result.status == TaskStatus.COMPLETED
    assert "page_name" in result.output_data
    assert result.output_data["route_path"] == "/users/:id"


@pytest.mark.asyncio
async def test_generate_hooks(code_frontend_agent: Any) -> None:
    """Test hook generation."""
    await code_frontend_agent.initialize()

    task = Task(
        id="test-3",
        type="generate_hooks",
        input_data={"hook_name": "useUserData", "framework": "react"},
    )

    result = await code_frontend_agent.execute(task)

    assert result.status == TaskStatus.COMPLETED
    assert "hook_name" in result.output_data
    assert result.output_data["hook_name"] == "useUserData"


@pytest.mark.asyncio
async def test_generate_services(code_frontend_agent: Any) -> None:
    """Test service generation."""
    await code_frontend_agent.initialize()

    task = Task(
        id="test-4",
        type="generate_services",
        input_data={"service_name": "userApi", "entity": "user", "framework": "react"},
    )

    result = await code_frontend_agent.execute(task)

    assert result.status == TaskStatus.COMPLETED
    assert "service_name" in result.output_data


@pytest.mark.asyncio
async def test_setup_project(code_frontend_agent: Any) -> None:
    """Test project setup."""
    await code_frontend_agent.initialize()

    task = Task(
        id="test-5",
        type="setup_project",
        input_data={"project_name": "my-frontend", "framework": "react", "typescript": False},
    )

    result = await code_frontend_agent.execute(task)

    assert result.status == TaskStatus.COMPLETED
    assert "files" in result.output_data
    assert "package.json" in result.output_data["files"]


@pytest.mark.asyncio
async def test_shutdown(code_frontend_agent: Any) -> None:
    """Test agent shutdown."""
    await code_frontend_agent.initialize()
    await code_frontend_agent.shutdown()

    assert code_frontend_agent.state.value == "idle"
