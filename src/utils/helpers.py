"""Helper utilities."""

import uuid
from datetime import datetime
from typing import Any, Dict


def generate_id() -> str:
    """Generar un ID único."""
    return str(uuid.uuid4())


def format_timestamp(dt: Optional[datetime] = None) -> str:
    """Formatear timestamp ISO."""
    if dt is None:
        dt = datetime.now()
    return dt.isoformat()


def parse_timestamp(ts: str) -> datetime:
    """Parsear timestamp ISO."""
    return datetime.fromisoformat(ts)


def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitizar diccionario removiendo valores sensibles."""
    sensitive_keys = ["password", "secret", "api_key", "token", "credential"]
    
    result = {}
    for key, value in data.items():
        if any(s in key.lower() for s in sensitive_keys):
            result[key] = "***"
        elif isinstance(value, dict):
            result[key] = sanitize_dict(value)
        elif isinstance(value, list):
            result[key] = [
                sanitize_dict(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[key] = value
    
    return result


def merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Mergear diccionarios recursivamente."""
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result


def truncate_string(s: str, max_length: int = 100) -> str:
    """Truncar string a longitud máxima."""
    if len(s) <= max_length:
        return s
    return s[:max_length - 3] + "..."


def safe_get(dictionary: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Obtener valor anidado de forma segura."""
    result = dictionary
    for key in keys:
        if isinstance(result, dict):
            result = result.get(key)
            if result is None:
                return default
        else:
            return default
    return result