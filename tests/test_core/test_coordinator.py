"""Tests for Coordinator."""

from typing import Any

import pytest

from src.agents.base.base_agent import Task
from src.agents.code.code_backend_agent import CodeBackendAgent
from src.agents.code.code_frontend_agent import CodeFrontendAgent
from src.agents.deploy.deploy_agent import DeployAgent
from src.agents.design.design_agent import DesignAgent
from src.agents.maintenance.maintenance_agent import MaintenanceAgent
from src.agents.requirements.requirements_agent import RequirementsAgent
from src.agents.requirements.requirements_agent_v2 import RequirementsAgentV2
from src.agents.tests.tests_agent import TestsAgent
from src.core.coordinator import Coordinator


@pytest.fixture
def coordinator() -> Any:
    """Create coordinator instance."""
    return Coordinator()


@pytest.fixture
def agents() -> Any:
    """Create agent instances."""
    return [RequirementsAgent(), DesignAgent(), CodeBackendAgent(), CodeFrontendAgent()]


@pytest.mark.asyncio
async def test_register_agent(coordinator: Any, agents: Any) -> None:
    """Test agent registration."""
    for agent in agents:
        coordinator.register_agent(agent)

    assert len(coordinator.list_agents()) == 4


@pytest.mark.asyncio
async def test_initialize_all(coordinator: Any, agents: Any) -> None:
    """Test initialization of all agents."""
    for agent in agents:
        coordinator.register_agent(agent)

    await coordinator.initialize_all()

    # Verify agents are initialized (state should be idle)
    for agent in agents:
        assert agent.state.value == "idle"


@pytest.mark.asyncio
async def test_submit_task(coordinator: Any, agents: Any) -> None:
    """Test task submission."""
    for agent in agents:
        coordinator.register_agent(agent)

    await coordinator.initialize_all()

    task = Task(id="test-1", type="gather_requirements", input_data={"project_description": "Test"})

    result = await coordinator.submit_task(task, agent_id="requirements")

    assert result.status.value == "completed"


@pytest.mark.asyncio
async def test_create_workflow(coordinator: Any, agents: Any) -> None:
    """Test workflow creation."""
    for agent in agents:
        coordinator.register_agent(agent)

    await coordinator.initialize_all()

    workflow_id = await coordinator.create_workflow(
        "full_development_cycle", {"project_name": "Test Project"}
    )

    assert workflow_id is not None

    status = await coordinator.get_workflow_status(workflow_id)
    assert status is not None
    assert status.name == "full_development_cycle"


@pytest.mark.asyncio
async def test_execute_workflow(coordinator: Any) -> None:
    """Test executing the full development workflow."""
    agents = [
        RequirementsAgentV2(),
        DesignAgent(),
        CodeBackendAgent(),
        CodeFrontendAgent(),
        TestsAgent(),
        DeployAgent(),
        MaintenanceAgent(),
    ]

    for agent in agents:
        coordinator.register_agent(agent)

    await coordinator.initialize_all()

    workflow_id = await coordinator.create_workflow(
        "full_development_cycle", {"project_name": "Test Project"}
    )

    workflow = await coordinator.execute_workflow(workflow_id)

    assert workflow.status.value == "completed"
    assert workflow.stages_completed == [
        coordinator.DEFAULT_WORKFLOW.stages[0],
        coordinator.DEFAULT_WORKFLOW.stages[1],
        coordinator.DEFAULT_WORKFLOW.stages[2],
        coordinator.DEFAULT_WORKFLOW.stages[3],
        coordinator.DEFAULT_WORKFLOW.stages[4],
        coordinator.DEFAULT_WORKFLOW.stages[5],
        coordinator.DEFAULT_WORKFLOW.stages[6],
    ]


@pytest.mark.asyncio
async def test_shutdown_all(coordinator: Any, agents: Any) -> None:
    """Test shutdown of all agents."""
    for agent in agents:
        coordinator.register_agent(agent)

    await coordinator.initialize_all()
    await coordinator.shutdown_all()

    for agent in agents:
        assert agent.state.value == "idle"
