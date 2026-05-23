"""Tests para utils."""

from datetime import datetime

from src.utils.config import Settings
from src.utils.helpers import (
    format_timestamp,
    generate_id,
    merge_dicts,
    parse_timestamp,
    safe_get,
    sanitize_dict,
    truncate_string,
)
from src.utils.logging import get_logger, setup_logging


class TestSettings:
    """Tests para Settings."""

    def test_settings_initialization(self) -> None:
        """Test inicialización de Settings."""
        settings = Settings()

        assert settings.app_name == "SDLAS"
        assert settings.app_version == "0.1.0"
        assert settings.debug is False

    def test_settings_llm_config(self) -> None:
        """Test configuración de LLM."""
        settings = Settings()

        assert settings.llm_provider == "Gemini"
        assert settings.llm_model == "gemini-3.5-flash"
        assert settings.llm_temperature == 0.7
        assert settings.llm_max_tokens == 2000

    def test_settings_agent_config(self) -> None:
        """Test configuración de agentes."""
        settings = Settings()

        assert settings.max_concurrent_tasks == 5
        assert settings.task_timeout == 300
        assert settings.agent_autonomy_level == 2

    def test_settings_logging_config(self) -> None:
        """Test configuración de logging."""
        settings = Settings()

        assert settings.log_level == "INFO"
        assert settings.log_format == "json"

    def test_settings_metrics_config(self) -> None:
        """Test configuración de métricas."""
        settings = Settings()

        assert settings.metrics_enabled is True
        assert settings.metrics_retention_days == 30


class TestHelpers:
    """Tests para helpers."""

    def test_generate_id(self) -> None:
        """Test generación de ID único."""
        id1 = generate_id()
        id2 = generate_id()

        assert id1 != id2
        assert len(id1) == 36  # UUID v4 format

    def test_format_timestamp(self) -> None:
        """Test formatear timestamp."""
        dt = datetime(2026, 5, 22, 10, 30, 45)
        formatted = format_timestamp(dt)

        assert "2026-05-22" in formatted
        assert "10:30:45" in formatted

    def test_format_timestamp_current(self) -> None:
        """Test formatear timestamp actual."""
        formatted = format_timestamp()

        assert len(formatted) > 0
        assert "T" in formatted  # ISO format

    def test_parse_timestamp(self) -> None:
        """Test parsear timestamp."""
        ts = "2026-05-22T10:30:45"
        parsed = parse_timestamp(ts)

        assert parsed.year == 2026
        assert parsed.month == 5
        assert parsed.day == 22
        assert parsed.hour == 10
        assert parsed.minute == 30

    def test_sanitize_dict_password(self) -> None:
        """Test sanitizar diccionario con password."""
        data = {
            "username": "admin",
            "password": "secret123",
            "email": "admin@example.com",
        }

        sanitized = sanitize_dict(data)

        assert sanitized["username"] == "admin"
        assert sanitized["password"] == "***"
        assert sanitized["email"] == "admin@example.com"

    def test_sanitize_dict_api_key(self) -> None:
        """Test sanitizar diccionario con API key."""
        data = {
            "service": "gemini",
            "api_key": "sk-1234567890",
            "endpoint": "https://api.example.com",
        }

        sanitized = sanitize_dict(data)

        assert sanitized["api_key"] == "***"
        assert sanitized["service"] == "gemini"

    def test_sanitize_dict_nested(self) -> None:
        """Test sanitizar diccionario anidado."""
        data = {
            "user": {
                "name": "John",
                "password": "secret",
            },
            "credentials": ["api_key_secret", "token_secret"],
        }

        sanitized = sanitize_dict(data)

        assert sanitized["user"]["password"] == "***"
        assert sanitized["user"]["name"] == "John"

    def test_merge_dicts(self) -> None:
        """Test mergear diccionarios."""
        base = {"a": 1, "b": 2, "c": {"x": 10}}
        override = {"b": 20, "c": {"y": 20}}

        result = merge_dicts(base, override)

        assert result["a"] == 1
        assert result["b"] == 20
        assert result["c"]["x"] == 10
        assert result["c"]["y"] == 20

    def test_merge_dicts_deep(self) -> None:
        """Test mergear diccionarios profundos."""
        base = {"config": {"db": {"host": "localhost", "port": 5432}}}
        override = {"config": {"db": {"port": 3306}}}

        result = merge_dicts(base, override)

        assert result["config"]["db"]["host"] == "localhost"
        assert result["config"]["db"]["port"] == 3306

    def test_truncate_string(self) -> None:
        """Test truncar string."""
        long_string = "a" * 150
        truncated = truncate_string(long_string, max_length=100)

        assert len(truncated) == 100
        assert truncated.endswith("...")

    def test_truncate_string_short(self) -> None:
        """Test truncar string corto."""
        short_string = "Hello, World!"
        truncated = truncate_string(short_string, max_length=50)

        assert truncated == short_string

    def test_safe_get_nested(self) -> None:
        """Test obtener valor anidado."""
        data = {
            "config": {
                "database": {
                    "host": "localhost",
                    "port": 5432,
                },
            },
        }

        value = safe_get(data, "config", "database", "host")

        assert value == "localhost"

    def test_safe_get_missing_key(self) -> None:
        """Test obtener clave faltante."""
        data: dict[str, dict[str, dict[str, str]]] = {"config": {"database": {"host": "localhost"}}}

        value = safe_get(data, "config", "cache", "host", default="default_value")

        assert value == "default_value"

    def test_safe_get_default(self) -> None:
        """Test valor por defecto."""
        data: dict[str, object] = {}

        value = safe_get(data, "nonexistent", "key", default=42)

        assert value == 42


class TestLogging:
    """Tests para logging."""

    def test_setup_logging_basic(self) -> None:
        """Test configurar logging básico."""
        # Ejecutar sin errores
        setup_logging(level="INFO", format_type="json")

    def test_setup_logging_debug(self) -> None:
        """Test configurar logging en DEBUG."""
        setup_logging(level="DEBUG", format_type="console")

    def test_get_logger(self) -> None:
        """Test obtener logger."""
        logger = get_logger("test_logger")

        assert logger is not None
        assert hasattr(logger, "info")
        assert hasattr(logger, "debug")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")

    def test_get_logger_different_names(self) -> None:
        """Test obtener múltiples loggers."""
        logger1 = get_logger("logger1")
        logger2 = get_logger("logger2")

        assert logger1 is not None
        assert logger2 is not None
