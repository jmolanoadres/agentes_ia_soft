"""Configuration management."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Configuración global del sistema."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # Configuración de la aplicación
    app_name: str = "SDLAS"
    app_version: str = "0.1.0"
    debug: bool = False
    
    # Configuración de LLM
    llm_provider: str = "openai"
    llm_model: str = "gpt-4"
    llm_api_key: Optional[str] = None
    llm_temperature: float = 0.7
    llm_max_tokens: int = 2000
    
    # Configuración de agentes
    max_concurrent_tasks: int = 5
    task_timeout: int = 300
    agent_autonomy_level: int = 2
    
    # Configuración de message broker
    message_broker_max_queue_size: int = 100
    message_ttl: int = 3600
    
    # Configuración de logging
    log_level: str = "INFO"
    log_format: str = "json"
    log_file: Optional[str] = None
    
    # Configuración de métricas
    metrics_enabled: bool = True
    metrics_retention_days: int = 30
    
    # Configuración de despliegue
    default_environment: str = "dev"
    docker_registry: Optional[str] = None
    kubernetes_enabled: bool = False


# Instancia global de configuración
settings = Settings()