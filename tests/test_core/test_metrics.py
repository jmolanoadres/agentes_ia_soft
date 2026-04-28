"""Tests for Metrics."""

import pytest
from src.core.metrics import MetricsCollector


@pytest.fixture
def metrics_collector():
    """Create metrics collector instance."""
    return MetricsCollector()


def test_record_agent_metric(metrics_collector):
    """Test recording agent metric."""
    metrics_collector.record_agent_metric("agent-1", "tasks_completed", 10)
    metrics_collector.record_agent_metric("agent-1", "tasks_failed", 2)
    
    metrics = metrics_collector.get_agent_metrics("agent-1")
    
    assert len(metrics) == 2


def test_record_system_metric(metrics_collector):
    """Test recording system metric."""
    metrics_collector.record_system_metric("cpu_usage", 45.5, "percent")
    metrics_collector.record_system_metric("memory_usage", 62.0, "percent")
    
    metrics = metrics_collector.get_system_metrics()
    
    assert len(metrics) == 2


def test_get_agent_summary(metrics_collector):
    """Test agent summary."""
    metrics_collector.record_agent_metric("agent-1", "tasks_completed", 10)
    metrics_collector.record_agent_metric("agent-1", "tasks_completed", 15)
    metrics_collector.record_agent_metric("agent-1", "execution_time", 5.2)
    
    summary = metrics_collector.get_agent_summary("agent-1")
    
    assert summary["agent_id"] == "agent-1"
    assert summary["total_metrics"] == 3
    assert "by_metric" in summary


def test_get_system_summary(metrics_collector):
    """Test system summary."""
    metrics_collector.record_system_metric("cpu_usage", 45.5, "percent")
    metrics_collector.record_system_metric("memory_usage", 62.0, "percent")
    
    summary = metrics_collector.get_system_summary()
    
    assert summary["total_metrics"] == 2
    assert "by_metric" in summary


def test_calculate_kpis(metrics_collector):
    """Test KPI calculation."""
    metrics_collector.record_agent_metric("agent-1", "tasks_completed", 10)
    metrics_collector.record_agent_metric("agent-1", "tasks_failed", 2)
    metrics_collector.record_agent_metric("agent-1", "execution_time", 5.0)
    
    kpis = metrics_collector.calculate_kpis()
    
    assert "task_completion_rate" in kpis
    assert "error_rate" in kpis
    assert "average_cycle_time" in kpis


def test_generate_report(metrics_collector):
    """Test report generation."""
    metrics_collector.record_agent_metric("agent-1", "tasks_completed", 10)
    metrics_collector.record_system_metric("cpu_usage", 45.5, "percent")
    
    report = metrics_collector.generate_report("daily")
    
    assert "period" in report
    assert "system_summary" in report
    assert "kpis" in report


def test_clear_agent_metrics(metrics_collector):
    """Test clearing agent metrics."""
    metrics_collector.record_agent_metric("agent-1", "tasks_completed", 10)
    
    count = metrics_collector.clear_agent_metrics("agent-1")
    
    assert count == 1
    assert len(metrics_collector.get_agent_metrics("agent-1")) == 0