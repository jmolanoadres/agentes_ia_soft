"""Tests para Event Bus."""

from datetime import datetime

import pytest

from src.core.event_bus import Event, EventBus


class TestEvent:
    """Tests para Event."""

    def test_event_creation(self) -> None:
        """Test creación de Event."""
        event = Event(
            id="evt-123",
            event_type="task_created",
            source="coordinator",
            data={"task_id": "task-456"},
        )

        assert event.id == "evt-123"
        assert event.event_type == "task_created"
        assert event.source == "coordinator"
        assert event.data == {"task_id": "task-456"}
        assert isinstance(event.timestamp, datetime)

    def test_event_with_metadata(self) -> None:
        """Test Event con metadata."""
        metadata = {"priority": "high", "retry_count": 0}
        event = Event(
            id="evt-789",
            event_type="agent_started",
            source="requirements_agent",
            metadata=metadata,
        )

        assert event.metadata == metadata

    def test_event_default_timestamp(self) -> None:
        """Test que Event tiene timestamp por defecto."""
        event = Event(
            id="evt-001",
            event_type="test",
            source="test_source",
        )

        assert event.timestamp is not None
        assert isinstance(event.timestamp, datetime)


class TestEventBus:
    """Tests para EventBus."""

    def test_event_bus_initialization(self) -> None:
        """Test inicialización de EventBus."""
        bus = EventBus()

        assert bus._subscribers == {}
        assert bus._event_history == []
        assert bus._max_history == 1000
        assert bus._global_subscribers == []

    def test_subscribe_to_event(self) -> None:
        """Test suscripción a evento."""
        bus = EventBus()
        handler_called = []

        def handler(event: Event) -> None:
            handler_called.append(event)

        sub_id = bus.subscribe("task_created", handler)

        assert sub_id is not None
        assert "task_created" in bus._subscribers
        assert handler in bus._subscribers["task_created"]

    def test_unsubscribe_from_event(self) -> None:
        """Test cancelar suscripción."""
        bus = EventBus()

        def handler(event: Event) -> None:
            pass

        bus.subscribe("test_event", handler)
        assert "test_event" in bus._subscribers
        assert len(bus._subscribers["test_event"]) == 1

        bus.unsubscribe("test_event", handler)
        assert len(bus._subscribers["test_event"]) == 0

    @pytest.mark.asyncio
    async def test_publish_event_to_subscribers(self) -> None:
        """Test publicar evento a suscriptores."""
        bus = EventBus()
        received_events = []

        def handler(event: Event) -> None:
            received_events.append(event)

        bus.subscribe("workflow_started", handler)

        event = Event(
            id="evt-wf-001",
            event_type="workflow_started",
            source="coordinator",
        )
        await bus.publish(event)

        assert len(received_events) == 1
        assert received_events[0].id == "evt-wf-001"

    @pytest.mark.asyncio
    async def test_publish_to_multiple_handlers(self) -> None:
        """Test publicar a múltiples handlers."""
        bus = EventBus()
        handler1_events = []
        handler2_events = []

        def handler1(event: Event) -> None:
            handler1_events.append(event)

        def handler2(event: Event) -> None:
            handler2_events.append(event)

        bus.subscribe("test_event", handler1)
        bus.subscribe("test_event", handler2)

        event = Event(id="evt-001", event_type="test_event", source="test")
        await bus.publish(event)

        assert len(handler1_events) == 1
        assert len(handler2_events) == 1

    @pytest.mark.asyncio
    async def test_event_history(self) -> None:
        """Test historial de eventos."""
        bus = EventBus()

        event1 = Event(id="evt-001", event_type="test", source="test")
        event2 = Event(id="evt-002", event_type="test", source="test")

        await bus.publish(event1)
        await bus.publish(event2)

        assert len(bus._event_history) == 2
        assert bus._event_history[0].id == "evt-001"
        assert bus._event_history[1].id == "evt-002"

    @pytest.mark.asyncio
    async def test_max_history_limit(self) -> None:
        """Test límite de historial."""
        bus = EventBus()
        bus._max_history = 5

        for i in range(10):
            event = Event(
                id=f"evt-{i:03d}",
                event_type="test",
                source="test",
            )
            await bus.publish(event)

        assert len(bus._event_history) <= bus._max_history

    def test_subscribe_to_all_events(self) -> None:
        """Test suscriptor global a todos los eventos."""
        bus = EventBus()
        all_events = []

        def global_handler(event: Event) -> None:
            all_events.append(event)

        bus.subscribe_global(global_handler)

        assert global_handler in bus._global_subscribers

    def test_unsubscribe_from_all_events(self) -> None:
        """Test cancelar suscriptor global."""
        bus = EventBus()

        def global_handler(event: Event) -> None:
            pass

        bus.subscribe_global(global_handler)
        assert len(bus._global_subscribers) == 1

        bus.unsubscribe_global(global_handler)
        assert len(bus._global_subscribers) == 0

    def test_get_subscribers_count(self) -> None:
        """Test obtener número de suscriptores."""
        bus = EventBus()

        def handler1(event: Event) -> None:
            pass

        def handler2(event: Event) -> None:
            pass

        bus.subscribe("event_type_1", handler1)
        bus.subscribe("event_type_1", handler2)

        count = bus.get_subscribers("event_type_1")

        assert count == 2

    def test_get_all_event_types(self) -> None:
        """Test obtener todos los tipos de eventos."""
        bus = EventBus()

        def handler(event: Event) -> None:
            pass

        bus.subscribe("event1", handler)
        bus.subscribe("event2", handler)
        bus.subscribe("event3", handler)

        event_types = bus.get_all_event_types()

        assert len(event_types) == 3
        assert "event1" in event_types
        assert "event2" in event_types
        assert "event3" in event_types

    @pytest.mark.asyncio
    async def test_get_event_history(self) -> None:
        """Test obtener historial de eventos."""
        bus = EventBus()

        event1 = Event(id="evt-001", event_type="type1", source="source1")
        event2 = Event(id="evt-002", event_type="type1", source="source1")
        event3 = Event(id="evt-003", event_type="type2", source="source2")

        await bus.publish(event1)
        await bus.publish(event2)
        await bus.publish(event3)

        history = bus.get_event_history(event_type="type1")

        assert len(history) == 2
        assert all(e.event_type == "type1" for e in history)

    @pytest.mark.asyncio
    async def test_get_event_history_by_source(self) -> None:
        """Test obtener historial por fuente."""
        bus = EventBus()

        event1 = Event(id="evt-001", event_type="test", source="agent_a")
        event2 = Event(id="evt-002", event_type="test", source="agent_b")
        event3 = Event(id="evt-003", event_type="test", source="agent_a")

        await bus.publish(event1)
        await bus.publish(event2)
        await bus.publish(event3)

        history = bus.get_event_history(source="agent_a")

        assert len(history) == 2
        assert all(e.source == "agent_a" for e in history)

    @pytest.mark.asyncio
    async def test_clear_history(self) -> None:
        """Test limpiar historial."""
        bus = EventBus()

        event = Event(id="evt-001", event_type="test", source="test")
        await bus.publish(event)

        assert len(bus._event_history) == 1

        count = bus.clear_history()

        assert count == 1
        assert len(bus._event_history) == 0

    def test_create_event(self) -> None:
        """Test crear evento con factory."""
        bus = EventBus()

        event = bus.create_event(
            event_type="custom_event",
            source="test_source",
            data={"key": "value"},
            metadata={"priority": "high"},
        )

        assert event.event_type == "custom_event"
        assert event.source == "test_source"
        assert event.data == {"key": "value"}
        assert event.metadata == {"priority": "high"}

