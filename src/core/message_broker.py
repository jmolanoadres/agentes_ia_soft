"""Message broker for inter-agent communication."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
import uuid

from src.agents.base.agent_protocol import AgentMessage, MessageType, Priority

logger = logging.getLogger(__name__)


@dataclass
class MessageQueue:
    """Cola de mensajes."""
    id: str
    receiver: str
    messages: List[AgentMessage] = field(default_factory=list)
    max_size: int = 100


class MessageBroker:
    """Broker de mensajes para comunicación interagentes."""
    
    def __init__(self, max_queue_size: int = 100):
        self._queues: Dict[str, MessageQueue] = {}
        self._subscribers: Dict[str, List[Callable]] = {}
        self._max_queue_size = max_queue_size
        self._processing = False
    
    async def publish(self, message: AgentMessage) -> None:
        """Publicar un mensaje."""
        receiver = message.receiver
        
        if receiver not in self._queues:
            self._queues[receiver] = MessageQueue(
                id=str(uuid.uuid4()),
                receiver=receiver,
                max_size=self._max_queue_size
            )
        
        queue = self._queues[receiver]
        
        if len(queue.messages) >= queue.max_size:
            logger.warning(f"Queue for {receiver} is full, dropping oldest message")
            queue.messages.pop(0)
        
        queue.messages.append(message)
        logger.debug(f"Message published to {receiver}: {message.id}")
        
        # Notificar suscriptores
        await self._notify_subscribers(receiver, message)
    
    async def subscribe(
        self,
        receiver: str,
        callback: Callable[[AgentMessage], None]
    ) -> None:
        """Suscribirse a mensajes de un receptor."""
        if receiver not in self._subscribers:
            self._subscribers[receiver] = []
        self._subscribers[receiver].append(callback)
        logger.info(f"Subscribed to messages for {receiver}")
    
    async def unsubscribe(
        self,
        receiver: str,
        callback: Callable[[AgentMessage], None]
    ) -> None:
        """Cancelar suscripción."""
        if receiver in self._subscribers:
            self._subscribers[receiver] = [
                cb for cb in self._subscribers[receiver] if cb != callback
            ]
    
    async def consume(self, receiver: str) -> Optional[AgentMessage]:
        """Consumir el siguiente mensaje para un receptor."""
        queue = self._queues.get(receiver)
        
        if not queue or not queue.messages:
            return None
        
        return queue.messages.pop(0)
    
    async def peek(self, receiver: str) -> Optional[AgentMessage]:
        """Ver el siguiente mensaje sin consumirlo."""
        queue = self._queues.get(receiver)
        
        if not queue or not queue.messages:
            return None
        
        return queue.messages[0]
    
    async def get_pending_count(self, receiver: str) -> int:
        """Obtener cantidad de mensajes pendientes."""
        queue = self._queues.get(receiver)
        
        if not queue:
            return 0
        
        return len(queue.messages)
    
    async def clear_queue(self, receiver: str) -> int:
        """Limpiar la cola de un receptor."""
        queue = self._queues.get(receiver)
        
        if not queue:
            return 0
        
        count = len(queue.messages)
        queue.messages.clear()
        
        logger.info(f"Cleared {count} messages for {receiver}")
        
        return count
    
    async def _notify_subscribers(
        self,
        receiver: str,
        message: AgentMessage
    ) -> None:
        """Notificar a los suscriptores."""
        callbacks = self._subscribers.get(receiver, [])
        
        for callback in callbacks:
            try:
                await callback(message)
            except Exception as e:
                logger.error(f"Error in subscriber callback: {e}")
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas de las colas."""
        stats = {}
        
        for receiver, queue in self._queues.items():
            stats[receiver] = {
                "pending": len(queue.messages),
                "max_size": queue.max_size
            }
        
        return stats
    
    async def broadcast(self, message: AgentMessage, receivers: List[str]) -> None:
        """Broadcast a multiple receivers."""
        for receiver in receivers:
            msg_copy = AgentMessage(
                id=str(uuid.uuid4()),
                sender=message.sender,
                receiver=receiver,
                message_type=message.message_type,
                priority=message.priority,
                payload=message.payload.copy(),
                correlation_id=message.correlation_id,
                metadata=message.metadata.copy()
            )
            await self.publish(msg_copy)