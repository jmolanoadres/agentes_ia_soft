"""Agent protocol for inter-agent communication."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import uuid


class MessageType(Enum):
    """Tipos de mensaje entre agentes."""
    TASK = "task"
    RESULT = "result"
    QUERY = "query"
    RESPONSE = "response"
    ERROR = "error"
    FEEDBACK = "feedback"
    APPROVAL = "approval"
    HEARTBEAT = "heartbeat"


class Priority(Enum):
    """Prioridad de mensajes."""
    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


@dataclass
class AgentMessage:
    """Mensaje entre agentes."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = ""
    receiver: str = ""
    message_type: MessageType = MessageType.TASK
    priority: Priority = Priority.NORMAL
    payload: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    expires_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir a diccionario."""
        return {
            "id": self.id,
            "sender": self.sender,
            "receiver": self.receiver,
            "message_type": self.message_type.value,
            "priority": self.priority.value,
            "payload": self.payload,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMessage":
        """Crear desde diccionario."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            sender=data.get("sender", ""),
            receiver=data.get("receiver", ""),
            message_type=MessageType(data.get("message_type", "task")),
            priority=Priority(data.get("priority", 5)),
            payload=data.get("payload", {}),
            correlation_id=data.get("correlation_id"),
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.now(),
            metadata=data.get("metadata", {}),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
        )


class MessageHandler(ABC):
    """Manejador de mensajes."""
    
    @abstractmethod
    async def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Procesar un mensaje."""
        pass
    
    @abstractmethod
    async def can_handle(self, message: AgentMessage) -> bool:
        """Determinar si puede manejar el mensaje."""
        pass


class Protocol:
    """Protocolo de comunicación entre agentes."""
    
    def __init__(self):
        self._handlers: Dict[MessageType, List[MessageHandler]] = {}
        self._message_queue: List[AgentMessage] = []
        self._processing = False
    
    def register_handler(self, message_type: MessageType, handler: MessageHandler) -> None:
        """Registrar un manejador para un tipo de mensaje."""
        if message_type not in self._handlers:
            self._handlers[message_type] = []
        self._handlers[message_type].append(handler)
    
    async def send_message(self, message: AgentMessage) -> None:
        """Enviar un mensaje."""
        self._message_queue.append(message)
    
    async def receive_message(self) -> Optional[AgentMessage]:
        """Recibir el siguiente mensaje."""
        if self._message_queue:
            return self._message_queue.pop(0)
        return None
    
    async def process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Procesar un mensaje con los handlers registrados."""
        handlers = self._handlers.get(message.message_type, [])
        
        for handler in handlers:
            if await handler.can_handle(message):
                return await handler.handle_message(message)
        
        return None
    
    def get_pending_messages(self, receiver: str) -> List[AgentMessage]:
        """Obtener mensajes pendientes para un receptor."""
        return [m for m in self._message_queue if m.receiver == receiver]
    
    def clear_expired_messages(self) -> int:
        """Limpiar mensajes expirados."""
        now = datetime.now()
        initial_count = len(self._message_queue)
        self._message_queue = [
            m for m in self._message_queue
            if m.expires_at is None or m.expires_at > now
        ]
        return initial_count - len(self._message_queue)


# Alias de compatibilidad hacia atrás
AgentProtocol = Protocol