"""Metrics collector for system monitoring."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from collections import defaultdict
import time

logger = logging.getLogger(__name__)


@dataclass
class AgentMetric:
    """Métrica de un agente."""
    agent_id: str
    metric_name: str
    value: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class SystemMetric:
    """Métrica del sistema."""
    metric_name: str
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.now)


class MetricsCollector:
    """Recolector y agregador de métricas del sistema."""
    
    def __init__(self):
        self._agent_metrics: Dict[str, List[AgentMetric]] = defaultdict(list)
        self._system_metrics: List[SystemMetric] = []
        self._max_metrics_per_agent = 1000
        self._max_system_metrics = 5000
    
    def record_agent_metric(
        self,
        agent_id: str,
        metric_name: str,
        value: float
    ) -> None:
        """Registrar una métrica de agente."""
        metric = AgentMetric(
            agent_id=agent_id,
            metric_name=metric_name,
            value=value,
            timestamp=datetime.now()
        )
        
        self._agent_metrics[agent_id].append(metric)
        
        # Limitar métricas por agente
        if len(self._agent_metrics[agent_id]) > self._max_metrics_per_agent:
            self._agent_metrics[agent_id].pop(0)
    
    def record_system_metric(
        self,
        metric_name: str,
        value: float,
        unit: str = ""
    ) -> None:
        """Registrar una métrica del sistema."""
        metric = SystemMetric(
            metric_name=metric_name,
            value=value,
            unit=unit,
            timestamp=datetime.now()
        )
        
        self._system_metrics.append(metric)
        
        # Limitar métricas del sistema
        if len(self._system_metrics) > self._max_system_metrics:
            self._system_metrics.pop(0)
    
    def get_agent_metrics(
        self,
        agent_id: str,
        metric_name: Optional[str] = None,
        limit: int = 100
    ) -> List[AgentMetric]:
        """Obtener métricas de un agente."""
        metrics = self._agent_metrics.get(agent_id, [])
        
        if metric_name:
            metrics = [m for m in metrics if m.metric_name == metric_name]
        
        return metrics[-limit:]
    
    def get_system_metrics(
        self,
        metric_name: Optional[str] = None,
        limit: int = 100
    ) -> List[SystemMetric]:
        """Obtener métricas del sistema."""
        metrics = self._system_metrics
        
        if metric_name:
            metrics = [m for m in metrics if m.metric_name == metric_name]
        
        return metrics[-limit:]
    
    def get_agent_summary(self, agent_id: str) -> Dict[str, Any]:
        """Obtener resumen de métricas de un agente."""
        metrics = self._agent_metrics.get(agent_id, [])
        
        if not metrics:
            return {"agent_id": agent_id, "metrics_count": 0}
        
        # Agrupar por nombre de métrica
        by_name = defaultdict(list)
        for m in metrics:
            by_name[m.metric_name].append(m.value)
        
        summary = {
            "agent_id": agent_id,
            "total_metrics": len(metrics),
            "by_metric": {}
        }
        
        for name, values in by_name.items():
            summary["by_metric"][name] = {
                "count": len(values),
                "latest": values[-1] if values else None,
                "average": sum(values) / len(values) if values else None,
                "min": min(values) if values else None,
                "max": max(values) if values else None
            }
        
        return summary
    
    def get_system_summary(self) -> Dict[str, Any]:
        """Obtener resumen de métricas del sistema."""
        if not self._system_metrics:
            return {"metrics_count": 0}
        
        # Agrupar por nombre de métrica
        by_name = defaultdict(list)
        for m in self._system_metrics:
            by_name[m.metric_name].append(m.value)
        
        summary = {
            "total_metrics": len(self._system_metrics),
            "unique_agents": len(self._agent_metrics),
            "by_metric": {}
        }
        
        for name, values in by_name.items():
            summary["by_metric"][name] = {
                "count": len(values),
                "latest": values[-1] if values else None,
                "average": sum(values) / len(values) if values else None,
                "min": min(values) if values else None,
                "max": max(values) if values else None
            }
        
        return summary
    
    def calculate_kpis(self) -> Dict[str, Any]:
        """Calcular KPIs del sistema."""
        kpis = {
            "task_completion_rate": 0.0,
            "average_cycle_time": 0.0,
            "error_rate": 0.0,
            "agent_utilization": {}
        }
        
        # Calcular task completion rate
        total_completed = 0
        total_failed = 0
        
        for agent_id, metrics in self._agent_metrics.items():
            completed = sum(1 for m in metrics if m.metric_name == "tasks_completed")
            failed = sum(1 for m in metrics if m.metric_name == "tasks_failed")
            total_completed += completed
            total_failed += failed
        
        total = total_completed + total_failed
        if total > 0:
            kpis["task_completion_rate"] = total_completed / total
            kpis["error_rate"] = total_failed / total
        
        # Calcular average cycle time
        cycle_times = []
        for metrics in self._agent_metrics.values():
            times = [m.value for m in metrics if m.metric_name == "execution_time"]
            cycle_times.extend(times)
        
        if cycle_times:
            kpis["average_cycle_time"] = sum(cycle_times) / len(cycle_times)
        
        # Calcular agent utilization
        for agent_id in self._agent_metrics.keys():
            metrics = self._agent_metrics[agent_id]
            total_tasks = sum(1 for m in metrics if m.metric_name in ["tasks_completed", "tasks_failed"])
            kpis["agent_utilization"][agent_id] = total_tasks
        
        return kpis
    
    def generate_report(self, period: str = "daily") -> Dict[str, Any]:
        """Generar informe de métricas."""
        return {
            "period": period,
            "generated_at": datetime.now().isoformat(),
            "system_summary": self.get_system_summary(),
            "kpis": self.calculate_kpis(),
            "agents": {
                agent_id: self.get_agent_summary(agent_id)
                for agent_id in self._agent_metrics.keys()
            }
        }
    
    def clear_agent_metrics(self, agent_id: str) -> int:
        """Limpiar métricas de un agente."""
        if agent_id in self._agent_metrics:
            count = len(self._agent_metrics[agent_id])
            self._agent_metrics[agent_id].clear()
            return count
        return 0
    
    def clear_system_metrics(self) -> int:
        """Limpiar métricas del sistema."""
        count = len(self._system_metrics)
        self._system_metrics.clear()
        return count