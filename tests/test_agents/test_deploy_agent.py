"""Tests for Deploy Agent."""

import pytest
from src.agents.deploy.deploy_agent import DeployAgent
from src.agents.base.base_agent import Task, TaskStatus


@pytest.fixture
def deploy_agent():
    """Create deploy agent instance."""
    return DeployAgent()


@pytest.mark.asyncio
async def test_initialization(deploy_agent):
    """Test agent initialization."""
    await deploy_agent.initialize()
    
    assert deploy_agent.state.value == "idle"
    assert len(deploy_agent.capabilities) > 0


@pytest.mark.asyncio
async def test_create_pipeline(deploy_agent):
    """Test pipeline creation."""
    await deploy_agent.initialize()
    
    task = Task(
        id="test-1",
        type="create_pipeline",
        input_data={
            "project_name": "Test Project",
            "stages": ["build", "test", "deploy"]
        }
    )
    
    result = await deploy_agent.execute(task)
    
    assert result.status == TaskStatus.COMPLETED
    assert "pipeline_id" in result.output_data
    assert "github_actions" in result.output_data


@pytest.mark.asyncio
async def test_configure_deployment(deploy_agent):
    """Test deployment configuration."""
    await deploy_agent.initialize()
    
    task = Task(
        id="test-2",
        type="configure_deployment",
        input_data={
            "environment": "production",
            "image_tag": "v1.0.0",
            "replicas": 3
        }
    )
    
    result = await deploy_agent.execute(task)
    
    assert result.status == TaskStatus.COMPLETED
    assert "config_id" in result.output_data
    assert result.output_data["environment"] == "production"


@pytest.mark.asyncio
async def test_execute_deployment(deploy_agent):
    """Test deployment execution."""
    await deploy_agent.initialize()
    
    task = Task(
        id="test-3",
        type="execute_deployment",
        input_data={
            "config_id": "config-1",
            "environment": "staging"
        }
    )
    
    result = await deploy_agent.execute(task)
    
    assert result.status == TaskStatus.COMPLETED
    assert "deployment_id" in result.output_data
    assert result.output_data["status"] == "deployed"


@pytest.mark.asyncio
async def test_rollback(deploy_agent):
    """Test rollback."""
    await deploy_agent.initialize()
    
    task = Task(
        id="test-4",
        type="rollback",
        input_data={
            "deployment_id": "deploy-1",
            "target_version": "v0.9.0"
        }
    )
    
    result = await deploy_agent.execute(task)
    
    assert result.status == TaskStatus.COMPLETED
    assert result.output_data["status"] == "rolled_back"


@pytest.mark.asyncio
async def test_shutdown(deploy_agent):
    """Test agent shutdown."""
    await deploy_agent.initialize()
    await deploy_agent.shutdown()
    
    assert deploy_agent.state.value == "idle"