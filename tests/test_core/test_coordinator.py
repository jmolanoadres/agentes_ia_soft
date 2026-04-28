"""Tests for Coordinator."""

import pytest
from src.core.coordinator import Coordinator, WorkflowStage, WorkflowStatus
from src.agents.requirements.requirements_agent import RequirementsAgent
from src.agents.design.design_agent import DesignAgent
from src.agents.code.code_backend_agent import CodeBackendAgent
from src.agents.code.code_frontend_agent import CodeFrontendAgent
from src.agents.base.base_agent import Task


@pytest.fixture
def coordinator():
    """Create coordinator instance."""
    return Coordinator()


@pytest.fixture
def agents():
    """Create agent instances."""
    return [RequirementsAgent(), DesignAgent(), CodeBackendAgent(), CodeFrontendAgent()]


@pytest.mark.asyncio
async def test_register_agent(coordinator, agents):
    """Test agent registration."""
    for agent in agents:
        coordinator.register_agent(agent)
    
    assert len(coordinator.list_agents()) == 2


@pytest.mark.asyncio
async def test_initialize_all(coordinator, agents):
    """Test initialization of all agents."""
    for agent in agents:
        coordinator.register_agent(agent)
    
    await coordinator.initialize_all()
    
    # Verify agents are initialized (state should be idle)
    for agent in agents:
        assert agent.state.value == "idle"


@pytest.mark.asyncio
async def test_submit_task(coordinator, agents):
    """Test task submission."""
    for agent in agents:
        coordinator.register_agent(agent)
    
    await coordinator.initialize_all()
    
    task = Task(
        id="test-1",
        type="gather_requirements",
        input_data={"project_description": "Test"}
    )
    
    result = await coordinator.submit_task(task, agent_id="requirements")
    
    assert result.status.value == "completed"


@pytest.mark.asyncio
async def test_create_workflow(coordinator, agents):
    """Test workflow creation."""
    for agent in agents:
        coordinator.register_agent(agent)
    
    await coordinator.initialize_all()
    
    workflow_id = await coordinator.create_workflow(
        "full_development_cycle",
        {"project_name": "Test Project"}
    )
    
    assert workflow_id is not None
    
    status = await coordinator.get_workflow_status(workflow_id)
    assert status is not None
    assert status.name == "full_development_cycle"


@pytest.mark.asyncio
async def test_shutdown_all(coordinator, agents):
    """Test shutdown of all agents."""
    for agent in agents:
        coordinator.register_agent(agent)
    
    await coordinator.initialize_all()
    await coordinator.shutdown_all()
    
    for agent in agents:
        assert agent.state.value == "idle"