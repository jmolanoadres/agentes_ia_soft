"""Maintenance agent for system monitoring and maintenance."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from src.agents.base.base_agent import BaseAgent, AgentState, Task, TaskResult, TaskStatus, Capability

logger = logging.getLogger(__name__)


@dataclass
class HealthMetric:
    """Métrica de salud del sistema."""
    name: str
    value: float
    unit: str
    status: str  # healthy, warning, critical
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class Alert:
    """Alerta del sistema."""
    id: str
    severity: str  # low, medium, high, critical
    message: str
    source: str
    timestamp: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
    resolved: bool = False


@dataclass
class SystemHealth:
    """Salud general del sistema."""
    overall_status: str
    uptime: float
    metrics: List[HealthMetric] = field(default_factory=list)
    alerts: List[Alert] = field(default_factory=list)
    last_check: datetime = field(default_factory=datetime.now)


class MaintenanceAgent(BaseAgent):
    """Agente especializado en mantenimiento y monitorización."""
    
    def __init__(self):
        super().__init__(
            agent_id="maintenance",
            name="Maintenance Agent",
            description="Agente para monitorización, mantenimiento y salud del sistema"
        )
        self._alerts: Dict[str, Alert] = {}
        self._health_history: List[SystemHealth] = []
        
        self._register_capabilities()
    
    def _register_capabilities(self) -> None:
        """Registrar las capacidades del agente."""
        self.add_capability(Capability(
            name="monitor_health",
            description="Monitorear salud del sistema",
            version="1.0.0"
        ))
        self.add_capability(Capability(
            name="detect_issues",
            description="Detectar issues y alertas",
            version="1.0.0"
        ))
        self.add_capability(Capability(
            name="analyze_logs",
            description="Analizar logs del sistema",
            version="1.0.0"
        ))
        self.add_capability(Capability(
            name="generate_reports",
            description="Generar informes de salud",
            version="1.0.0"
        ))
        self.add_capability(Capability(
            name="suggest_improvements",
            description="Sugerir mejoras continuas",
            version="1.0.0"
        ))
    
    async def initialize(self) -> None:
        """Inicializar el agente."""
        self.update_state(AgentState.INITIALIZING)
        logger.info(f"Initializing {self._name}")
        self.update_state(AgentState.IDLE)
    
    async def execute(self, task: Task) -> TaskResult:
        """Ejecutar una tarea de mantenimiento."""
        start_time = datetime.now()
        self.update_state(AgentState.PROCESSING)
        
        try:
            task_type = task.type
            
            if task_type == "monitor_health":
                result = await self._monitor_health(task.input_data)
            elif task_type == "detect_issues":
                result = await self._detect_issues(task.input_data)
            elif task_type == "analyze_logs":
                result = await self._analyze_logs(task.input_data)
            elif task_type == "generate_reports":
                result = await self._generate_reports(task.input_data)
            elif task_type == "suggest_improvements":
                result = await self._suggest_improvements(task.input_data)
            else:
                raise ValueError(f"Unknown task type: {task_type}")
            
            execution_time = (datetime.now() - start_time).total_seconds()
            self.update_metrics(execution_time, success=True)
            self.update_state(AgentState.IDLE)
            
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                output_data=result,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.update_metrics(execution_time, success=False)
            self.update_state(AgentState.ERROR)
            logger.error(f"Error executing task: {e}")
            
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                error=str(e),
                execution_time=execution_time
            )
    
    async def _monitor_health(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Monitorear salud del sistema."""
        # Simular métricas de salud
        metrics = [
            HealthMetric(name="cpu_usage", value=45.2, unit="percent", status="healthy"),
            HealthMetric(name="memory_usage", value=62.8, unit="percent", status="healthy"),
            HealthMetric(name="disk_usage", value=38.5, unit="percent", status="healthy"),
            HealthMetric(name="response_time", value=125.0, unit="ms", status="healthy"),
            HealthMetric(name="error_rate", value=0.5, unit="percent", status="healthy"),
            HealthMetric(name="request_rate", value=150.0, unit="req/s", status="healthy"),
        ]
        
        # Determinar estado general
        overall_status = "healthy"
        if any(m.status == "critical" for m in metrics):
            overall_status = "critical"
        elif any(m.status == "warning" for m in metrics):
            overall_status = "warning"
        
        health = SystemHealth(
            overall_status=overall_status,
            uptime=99.8,
            metrics=metrics,
            alerts=[],
            last_check=datetime.now()
        )
        
        self._health_history.append(health)
        
        return {
            "overall_status": health.overall_status,
            "uptime": health.uptime,
            "metrics": [self._metric_to_dict(m) for m in metrics],
            "last_check": health.last_check.isoformat()
        }
    
    async def _detect_issues(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Detectar issues y alertas."""
        # Simular detección de issues
        new_alerts = []
        
        # Verificar métricas
        cpu = input_data.get("cpu_usage", 0)
        memory = input_data.get("memory_usage", 0)
        error_rate = input_data.get("error_rate", 0)
        
        if cpu > 80:
            alert = Alert(
                id=str(uuid.uuid4()),
                severity="high",
                message=f"High CPU usage: {cpu}%",
                source="system"
            )
            new_alerts.append(alert)
            self._alerts[alert.id] = alert
        
        if memory > 85:
            alert = Alert(
                id=str(uuid.uuid4()),
                severity="critical",
                message=f"High memory usage: {memory}%",
                source="system"
            )
            new_alerts.append(alert)
            self._alerts[alert.id] = alert
        
        if error_rate > 5:
            alert = Alert(
                id=str(uuid.uuid4()),
                severity="high",
                message=f"High error rate: {error_rate}%",
                source="application"
            )
            new_alerts.append(alert)
            self._alerts[alert.id] = alert
        
        return {
            "alerts_detected": len(new_alerts),
            "alerts": [self._alert_to_dict(a) for a in new_alerts],
            "total_active_alerts": len([a for a in self._alerts.values() if not a.resolved])
        }
    
    async def _analyze_logs(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analizar logs del sistema."""
        log_pattern = input_data.get("log_pattern", "error")
        time_range = input_data.get("time_range", "1h")
        
        # Simular análisis de logs
        analysis = {
            "total_logs": 1250,
            "error_count": 15,
            "warning_count": 45,
            "info_count": 1190,
            "patterns": [
                {"pattern": "Connection timeout", "count": 5, "severity": "error"},
                {"pattern": "Invalid input", "count": 8, "severity": "warning"},
                {"pattern": "Cache miss", "count": 12, "severity": "info"}
            ],
            "recommendations": [
                "Revisar timeouts de conexión",
                "Optimizar validación de entrada"
            ]
        }
        
        return analysis
    
    async def _generate_reports(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generar informes de salud."""
        period = input_data.get("period", "daily")
        
        # Calcular estadísticas del período
        total_alerts = len(self._alerts)
        resolved_alerts = len([a for a in self._alerts.values() if a.resolved])
        
        avg_uptime = 99.5  # Simulado
        
        report = {
            "period": period,
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_alerts": total_alerts,
                "resolved_alerts": resolved_alerts,
                "resolution_rate": resolved_alerts / total_alerts if total_alerts > 0 else 0,
                "average_uptime": avg_uptime
            },
            "top_issues": [
                {"issue": "High memory usage", "occurrences": 3},
                {"issue": "Connection timeouts", "occurrences": 5}
            ],
            "recommendations": [
                "Incrementar recursos de memoria",
                "Revisar configuración de conexiones"
            ]
        }
        
        return report
    
    async def _suggest_improvements(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Sugerir mejoras continuas."""
        # Analizar estado actual y sugerir mejoras
        suggestions = []
        
        # Sugerencias basadas en análisis
        suggestions.append({
            "category": "performance",
            "title": "Optimizar caché",
            "description": "Implementar caché Redis para reducir latencia",
            "impact": "high",
            "effort": "medium"
        })
        
        suggestions.append({
            "category": "reliability",
            "title": "Configurar health checks",
            "description": "Añadir health checks más granulares",
            "impact": "medium",
            "effort": "low"
        })
        
        suggestions.append({
            "category": "security",
            "title": "Rotar secretos",
            "description": "Implementar rotación automática de secretos",
            "impact": "high",
            "effort": "medium"
        })
        
        return {
            "suggestions": suggestions,
            "count": len(suggestions),
            "prioritized": True
        }
    
    async def shutdown(self) -> None:
        """Limpiar recursos."""
        self.update_state(AgentState.SHUTTING_DOWN)
        logger.info(f"Shutting down {self._name}")
        self.update_state(AgentState.IDLE)
    
    def _metric_to_dict(self, metric: HealthMetric) -> Dict[str, Any]:
        """Convertir métrica a diccionario."""
        return {
            "name": metric.name,
            "value": metric.value,
            "unit": metric.unit,
            "status": metric.status,
            "timestamp": metric.timestamp.isoformat()
        }
    
    def _alert_to_dict(self, alert: Alert) -> Dict[str, Any]:
        """Convertir alerta a diccionario."""
        return {
            "id": alert.id,
            "severity": alert.severity,
            "message": alert.message,
            "source": alert.source,
            "timestamp": alert.timestamp.isoformat(),
            "acknowledged": alert.acknowledged,
            "resolved": alert.resolved
        }
    
    def get_alerts(self) -> Dict[str, Alert]:
        """Obtener alertas."""
        return self._alerts
    
    def get_health_history(self) -> List[SystemHealth]:
        """Obtener historial de salud."""
        return self._health_history