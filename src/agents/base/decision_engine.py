"""Decision engine for autonomous agent decision-making."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class DecisionConfidence(Enum):
    """Nivel de confianza en una decisión."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class DecisionType(Enum):
    """Tipos de decisión."""
    TASK_SELECTION = "task_selection"
    STRATEGY_CHOICE = "strategy_choice"
    RESOURCE_ALLOCATION = "resource_allocation"
    ERROR_RECOVERY = "error_recovery"
    ESCALATION = "escalation"
    APPROVAL = "approval"


class ErrorSeverity(Enum):
    """Severidad de errores."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DecisionOption:
    """Opción evaluable para una decisión."""
    id: str
    description: str
    pros: List[str] = field(default_factory=list)
    cons: List[str] = field(default_factory=list)
    score: float = 0.0
    risk_level: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Decision:
    """Representa una decisión tomada."""
    id: str
    decision_type: DecisionType
    selected_option: DecisionOption
    confidence: DecisionConfidence
    reasoning: str
    alternatives_considered: List[DecisionOption] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)
    requires_approval: bool = False
    approved_by: Optional[str] = None


@dataclass
class RecoveryAction:
    """Acción de recuperación ante errores."""
    action_type: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    max_retries: int = 3
    backoff_multiplier: float = 2.0
    fallback_action: Optional["RecoveryAction"] = None


class DecisionRule(ABC):
    """Regla base para decisiones."""
    
    @abstractmethod
    async def evaluate(
        self,
        context: Dict[str, Any],
        options: List[DecisionOption]
    ) -> List[DecisionOption]:
        """Evaluar opciones según la regla."""
        pass


class CostBenefitRule(DecisionRule):
    """Regla basada en costo-beneficio."""
    
    def __init__(self, cost_weight: float = 0.5, benefit_weight: float = 0.5):
        self.cost_weight = cost_weight
        self.benefit_weight = benefit_weight
    
    async def evaluate(
        self,
        context: Dict[str, Any],
        options: List[DecisionOption]
    ) -> List[DecisionOption]:
        for option in options:
            # Score basado en pros vs cons
            pros_score = len(option.pros) * self.benefit_weight
            cons_penalty = len(option.cons) * self.cost_weight
            option.score = max(0, pros_score - cons_penalty)
        
        return sorted(options, key=lambda x: x.score, reverse=True)


class RiskAdjustedRule(DecisionRule):
    """Regla que ajusta por riesgo."""
    
    async def evaluate(
        self,
        context: Dict[str, Any],
        options: List[DecisionOption]
    ) -> List[DecisionOption]:
        for option in options:
            # Ajustar score por riesgo
            risk_adjustment = 1.0 - (option.risk_level * 0.5)
            option.score = option.score * risk_adjustment
        
        return sorted(options, key=lambda x: x.score, reverse=True)


class DecisionEngine:
    """Motor de decisiones para agentes autónomos."""
    
    def __init__(self):
        self._rules: Dict[DecisionType, DecisionRule] = {}
        self._decision_history: List[Decision] = []
        self._max_history = 1000
        self._callbacks: Dict[DecisionType, List[Callable]] = {}
    
    def register_rule(self, decision_type: DecisionType, rule: DecisionRule) -> None:
        """Registrar una regla de decisión."""
        self._rules[decision_type] = rule
    
    def register_callback(
        self,
        decision_type: DecisionType,
        callback: Callable[[Decision], None]
    ) -> None:
        """Registrar callback para después de una decisión."""
        if decision_type not in self._callbacks:
            self._callbacks[decision_type] = []
        self._callbacks[decision_type].append(callback)
    
    async def evaluate_options(
        self,
        decision_type: DecisionType,
        context: Dict[str, Any],
        options: List[DecisionOption]
    ) -> Decision:
        """Evaluar opciones y tomar una decisión."""
        import uuid
        
        rule = self._rules.get(decision_type)
        if rule:
            evaluated_options = await rule.evaluate(context, options)
        else:
            evaluated_options = sorted(options, key=lambda x: x.score, reverse=True)
        
        selected = evaluated_options[0] if evaluated_options else options[0]
        
        # Calcular confianza basada en diferencia de scores
        confidence = DecisionConfidence.MEDIUM
        if len(evaluated_options) > 1:
            score_diff = evaluated_options[0].score - evaluated_options[1].score
            if score_diff > 0.8:
                confidence = DecisionConfidence.VERY_HIGH
            elif score_diff > 0.5:
                confidence = DecisionConfidence.HIGH
            elif score_diff > 0.2:
                confidence = DecisionConfidence.MEDIUM
            else:
                confidence = DecisionConfidence.LOW
        
        decision = Decision(
            id=str(uuid.uuid4()),
            decision_type=decision_type,
            selected_option=selected,
            confidence=confidence,
            reasoning=f"Selected option based on {decision_type.value} rule",
            alternatives_considered=evaluated_options[1:5] if len(evaluated_options) > 1 else [],
            context=context,
        )
        
        # Guardar en historial
        self._decision_history.append(decision)
        if len(self._decision_history) > self._max_history:
            self._decision_history.pop(0)
        
        # Ejecutar callbacks
        for callback in self._callbacks.get(decision_type, []):
            callback(decision)
        
        logger.info(f"Decision taken: {decision.decision_type.value} - {selected.id}")
        
        return decision
    
    async def handle_exception(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> RecoveryAction:
        """Manejar una excepción y determinar acción de recuperación."""
        error_type = type(error).__name__
        error_msg = str(error)
        
        # Clasificar severidad
        severity = ErrorSeverity.MEDIUM
        if "timeout" in error_msg.lower() or "connection" in error_msg.lower():
            severity = ErrorSeverity.HIGH
        if "authentication" in error_msg.lower() or "permission" in error_msg.lower():
            severity = ErrorSeverity.CRITICAL
        
        # Determinar acción según tipo de error
        if "timeout" in error_type.lower():
            action = RecoveryAction(
                action_type="retry",
                description="Reintentar operación con backoff",
                parameters={"timeout": context.get("timeout", 30)},
                max_retries=3,
                backoff_multiplier=2.0,
            )
        elif "connection" in error_type.lower():
            action = RecoveryAction(
                action_type="reconnect",
                description="Reconectar y reintentar",
                parameters={},
                max_retries=5,
                backoff_multiplier=1.5,
            )
        elif "authentication" in error_type.lower():
            action = RecoveryAction(
                action_type="escalate",
                description="Escalar a operador humano",
                parameters={"reason": "Authentication error"},
                max_retries=0,
            )
        else:
            action = RecoveryAction(
                action_type="retry",
                description="Reintentar operación",
                parameters={},
                max_retries=3,
                backoff_multiplier=1.0,
            )
        
        logger.warning(f"Exception handled: {error_type} - severity: {severity.value}")
        
        return action
    
    def get_decision_history(
        self,
        decision_type: Optional[DecisionType] = None,
        limit: int = 100
    ) -> List[Decision]:
        """Obtener historial de decisiones."""
        if decision_type:
            filtered = [d for d in self._decision_history if d.decision_type == decision_type]
            return filtered[-limit:]
        return self._decision_history[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Obtener estadísticas de decisiones."""
        if not self._decision_history:
            return {"total_decisions": 0}
        
        confidence_counts = {}
        type_counts = {}
        
        for decision in self._decision_history:
            conf = decision.confidence.value
            confidence_counts[conf] = confidence_counts.get(conf, 0) + 1
            
            dtype = decision.decision_type.value
            type_counts[dtype] = type_counts.get(dtype, 0) + 1
        
        return {
            "total_decisions": len(self._decision_history),
            "by_confidence": confidence_counts,
            "by_type": type_counts,
            "requires_approval_count": sum(1 for d in self._decision_history if d.requires_approval),
        }