"""Event bus for system-wide event handling."""

import asyncio
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """Evento del sistema."""

    id: str
    event_type: str
    source: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


class EventBus:
    """Bus de eventos para comunicación basada en eventos."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[Event], None]]] = {}
        self._event_history: list[Event] = []
        self._max_history = 1000
        self._global_subscribers: list[Callable[[Event], None]] = []

    def subscribe(self, event_type: str, handler: Callable[[Event], None]) -> str:
        """Suscribirse a un tipo de evento."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []

        self._subscribers[event_type].append(handler)

        subscription_id = str(uuid.uuid4())
        logger.info(f"Subscribed to event type: {event_type}")

        return subscription_id

    def unsubscribe(self, event_type: str, handler: Callable[[Event], None]) -> None:
        """Cancelar suscripción a un tipo de evento."""
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                h for h in self._subscribers[event_type] if h != handler
            ]

    def subscribe_global(self, handler: Callable[[Event], None]) -> str:
        """Suscribirse a todos los eventos."""
        self._global_subscribers.append(handler)

        subscription_id = str(uuid.uuid4())
        logger.info("Subscribed to all events")

        return subscription_id

    def unsubscribe_global(self, handler: Callable[[Event], None]) -> None:
        """Cancelar suscripción global."""
        self._global_subscribers = [h for h in self._global_subscribers if h != handler]

    async def publish(self, event: Event) -> None:
        """Publicar un evento."""
        self._event_history.append(event)

        # Limitar historial
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)

        # Notificar suscriptores específicos
        handlers = self._subscribers.get(event.event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")

        # Notificar suscriptores globales
        for handler in self._global_subscribers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Error in global event handler: {e}")

        logger.debug(f"Event published: {event.event_type} from {event.source}")

    def create_event(
        self,
        event_type: str,
        source: str,
        data: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Event:
        """Crear un nuevo evento."""
        return Event(
            id=str(uuid.uuid4()),
            event_type=event_type,
            source=source,
            data=data or {},
            metadata=metadata or {},
        )

    def get_event_history(
        self, event_type: str | None = None, source: str | None = None, limit: int = 100
    ) -> list[Event]:
        """Obtener historial de eventos."""
        events = self._event_history

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        if source:
            events = [e for e in events if e.source == source]

        return events[-limit:]

    def get_subscribers(self, event_type: str) -> int:
        """Obtener número de suscriptores para un tipo de evento."""
        return len(self._subscribers.get(event_type, []))

    def get_all_event_types(self) -> list[str]:
        """Obtener todos los tipos de eventos con suscriptores."""
        return list(self._subscribers.keys())

    def clear_history(self) -> int:
        """Limpiar historial de eventos."""
        count = len(self._event_history)
        self._event_history.clear()
        logger.info(f"Cleared event history: {count} events")
        return count
