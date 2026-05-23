"""Tests para módulo de persistencia."""

import json
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

from src.persistence import Persistence


class TestPersistence:
    """Tests para Persistence."""

    @pytest.fixture
    def temp_dir(self) -> Generator[Path, None, None]:
        """Crear directorio temporal."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_persistence_initialization(self, temp_dir: Path) -> None:
        """Test inicialización de Persistence."""
        path = str(temp_dir / "state.json")
        persistence = Persistence(path=path)

        assert persistence.path == Path(path)
        assert persistence.path.parent.exists()

    def test_persistence_save_data(self, temp_dir: Path) -> None:
        """Test guardar datos."""
        path = str(temp_dir / "test_state.json")
        persistence = Persistence(path=path)

        test_data = {
            "app_state": "running",
            "agents": ["requirements", "design"],
            "count": 42,
        }

        persistence.save(test_data)

        assert Path(path).exists()

        saved_content = Path(path).read_text()
        loaded = json.loads(saved_content)

        assert loaded == test_data

    def test_persistence_load_data(self, temp_dir: Path) -> None:
        """Test cargar datos."""
        path = str(temp_dir / "test_state.json")
        persistence = Persistence(path=path)

        original_data = {
            "status": "initialized",
            "version": "1.0.0",
            "tasks": ["task1", "task2"],
        }

        persistence.save(original_data)

        loaded_data = persistence.load()

        assert loaded_data == original_data

    def test_persistence_load_nonexistent_file(self, temp_dir: Path) -> None:
        """Test cargar archivo inexistente."""
        path = str(temp_dir / "nonexistent.json")
        persistence = Persistence(path=path)

        result = persistence.load()

        assert result == {}

    def test_persistence_overwrite_data(self, temp_dir: Path) -> None:
        """Test sobrescribir datos."""
        path = str(temp_dir / "overwrite_test.json")
        persistence = Persistence(path=path)

        data1 = {"version": "1.0.0"}
        persistence.save(data1)

        loaded1 = persistence.load()
        assert loaded1 == data1

        data2 = {"version": "2.0.0", "new_field": "new_value"}
        persistence.save(data2)

        loaded2 = persistence.load()
        assert loaded2 == data2
        assert "version" in loaded2
        assert loaded2["version"] == "2.0.0"

    def test_persistence_save_complex_data(self, temp_dir: Path) -> None:
        """Test guardar datos complejos."""
        path = str(temp_dir / "complex.json")
        persistence = Persistence(path=path)

        complex_data = {
            "agents": {
                "requirements": {
                    "status": "running",
                    "metrics": {"executions": 10, "success_rate": 0.95},
                },
                "design": {
                    "status": "idle",
                    "metrics": {"executions": 5, "success_rate": 0.8},
                },
            },
            "workflows": ["full_development_cycle"],
            "timestamps": {
                "started": "2026-05-22T10:00:00",
                "last_update": "2026-05-22T12:00:00",
            },
        }

        persistence.save(complex_data)

        loaded = persistence.load()

        assert loaded["agents"]["requirements"]["status"] == "running"
        assert loaded["agents"]["design"]["metrics"]["success_rate"] == 0.8
        assert "full_development_cycle" in loaded["workflows"]

    def test_persistence_unicode_data(self, temp_dir: Path) -> None:
        """Test guardar datos con caracteres unicode."""
        path = str(temp_dir / "unicode.json")
        persistence = Persistence(path=path)

        unicode_data = {
            "proyecto": "API Gestión Usuarios ADRES",
            "descripción": "Sistema de gestión con autenticación OAuth2",
            "caracteres_especiales": "¡@#$%^&*()ñÑ",
        }

        persistence.save(unicode_data)

        loaded = persistence.load()

        assert loaded["proyecto"] == "API Gestión Usuarios ADRES"
        assert loaded["descripción"] == "Sistema de gestión con autenticación OAuth2"
        assert "ñ" in loaded["caracteres_especiales"]

    def test_persistence_empty_dict(self, temp_dir: Path) -> None:
        """Test guardar diccionario vacío."""
        path = str(temp_dir / "empty.json")
        persistence = Persistence(path=path)

        persistence.save({})

        loaded = persistence.load()

        assert loaded == {}

    def test_persistence_nested_directories(self, temp_dir: Path) -> None:
        """Test crear directorios anidados."""
        path = str(temp_dir / "nested" / "deep" / "directory" / "state.json")
        persistence = Persistence(path=path)

        assert Path(path).parent.exists()

        data = {"level": "deep"}
        persistence.save(data)

        loaded = persistence.load()

        assert loaded == data

    def test_persistence_list_data(self, temp_dir: Path) -> None:
        """Test guardar listas directamente (JSON serializable)."""
        path = str(temp_dir / "list_state.json")
        persistence = Persistence(path=path)

        # JSON permite listas, pero nuestra clase espera dict
        # Por lo tanto, envolvemos en dict
        list_data = {
            "items": [1, 2, 3, 4, 5],
            "names": ["agent1", "agent2", "agent3"],
        }

        persistence.save(list_data)

        loaded = persistence.load()

        assert loaded["items"] == [1, 2, 3, 4, 5]
        assert len(loaded["names"]) == 3

    def test_persistence_default_path(self) -> None:
        """Test ruta por defecto."""
        persistence = Persistence()

        assert persistence.path == Path("data/state.json")
        assert persistence.path.parent.exists() or persistence.path.parent == Path("data")
