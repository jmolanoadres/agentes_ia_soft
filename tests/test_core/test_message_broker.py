"""Tests for Message Broker."""

from typing import Any

import pytest

from src.agents.base.agent_protocol import AgentMessage, MessageType, Priority
from src.core.message_broker import MessageBroker


@pytest.fixture
def message_broker() -> Any:
    """Create message broker instance."""
    return MessageBroker(max_queue_size=10)


@pytest.mark.asyncio
async def test_publish_message(message_broker: Any) -> None:
    """Test message publishing."""
    message = AgentMessage(
        sender="agent-1",
        receiver="agent-2",
        message_type=MessageType.TASK,
        priority=Priority.NORMAL,
        payload={"task": "test"},
    )

    await message_broker.publish(message)

    count = await message_broker.get_pending_count("agent-2")
    assert count == 1


@pytest.mark.asyncio
async def test_consume_message(message_broker: Any) -> None:
    """Test message consumption."""
    message = AgentMessage(
        sender="agent-1",
        receiver="agent-2",
        message_type=MessageType.TASK,
        payload={"task": "test"},
    )

    await message_broker.publish(message)
    consumed = await message_broker.consume("agent-2")

    assert consumed is not None
    assert consumed.sender == "agent-1"


@pytest.mark.asyncio
async def test_subscribe(message_broker: Any) -> None:
    """Test subscription."""
    received: list[AgentMessage] = []

    async def callback(msg: AgentMessage) -> None:
        received.append(msg)

    await message_broker.subscribe("agent-2", callback)

    message = AgentMessage(
        sender="agent-1", receiver="agent-2", message_type=MessageType.TASK, payload={}
    )

    await message_broker.publish(message)

    # Give time for callback
    assert len(received) == 1


@pytest.mark.asyncio
async def test_clear_queue(message_broker: Any) -> None:
    """Test queue clearing."""
    message = AgentMessage(
        sender="agent-1", receiver="agent-2", message_type=MessageType.TASK, payload={}
    )

    await message_broker.publish(message)
    await message_broker.publish(message)

    count = await message_broker.clear_queue("agent-2")

    assert count == 2
    assert await message_broker.get_pending_count("agent-2") == 0


@pytest.mark.asyncio
async def test_broadcast(message_broker: Any) -> None:
    """Test broadcast to multiple receivers."""
    message = AgentMessage(sender="agent-1", receiver="", message_type=MessageType.TASK, payload={})

    await message_broker.broadcast(message, ["agent-2", "agent-3", "agent-4"])

    assert await message_broker.get_pending_count("agent-2") == 1
    assert await message_broker.get_pending_count("agent-3") == 1
    assert await message_broker.get_pending_count("agent-4") == 1
