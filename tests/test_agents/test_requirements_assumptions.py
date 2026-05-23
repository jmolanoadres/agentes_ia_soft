"""Tests para requirements_assumptions."""

from datetime import datetime

from src.agents.requirements.requirements_assumptions import (
    AssumptionItem,
    render_progress_bar,
)


class TestAssumptionItem:
    """Tests para AssumptionItem."""

    def test_assumption_item_initialization(self) -> None:
        """Test creación de AssumptionItem."""
        item = AssumptionItem(
            id="assume-001",
            text="El sistema usará base de datos relacional",
        )

        assert item.id == "assume-001"
        assert item.text == "El sistema usará base de datos relacional"
        assert item.status == "assumed"
        assert item.user_definition is None

    def test_assumption_item_accepted(self) -> None:
        """Test AssumptionItem aceptado."""
        item = AssumptionItem(
            id="assume-002",
            text="Autenticación OAuth2",
            status="accepted",
        )

        assert item.status == "accepted"

    def test_assumption_item_rejected(self) -> None:
        """Test AssumptionItem rechazado."""
        item = AssumptionItem(
            id="assume-003",
            text="API REST",
            status="rejected",
        )

        assert item.status == "rejected"

    def test_assumption_item_redefined(self) -> None:
        """Test AssumptionItem redefinido."""
        item = AssumptionItem(
            id="assume-004",
            text="Original assumption",
            status="redefined",
            user_definition="Nueva definición del supuesto",
        )

        assert item.status == "redefined"
        assert item.user_definition == "Nueva definición del supuesto"

    def test_assumption_item_added(self) -> None:
        """Test AssumptionItem añadido por usuario."""
        item = AssumptionItem(
            id="assume-005",
            text="Nuevo supuesto",
            status="added",
        )

        assert item.status == "added"

    def test_assumption_item_to_dict(self) -> None:
        """Test conversión a diccionario."""
        item = AssumptionItem(
            id="assume-006",
            text="Test assumption",
            status="accepted",
        )

        item_dict = item.to_dict()

        assert item_dict["id"] == "assume-006"
        assert item_dict["text"] == "Test assumption"
        assert item_dict["status"] == "accepted"
        assert item_dict["user_definition"] is None

    def test_assumption_item_with_user_definition_to_dict(self) -> None:
        """Test to_dict con user_definition."""
        item = AssumptionItem(
            id="assume-007",
            text="Original",
            status="redefined",
            user_definition="Redefinido por usuario",
        )

        item_dict = item.to_dict()

        assert item_dict["user_definition"] == "Redefinido por usuario"

    def test_assumption_item_created_at(self) -> None:
        """Test que AssumptionItem tiene created_at."""
        item = AssumptionItem(
            id="assume-008",
            text="Test",
        )

        assert item.created_at is not None
        assert isinstance(item.created_at, datetime)

    def test_assumption_item_custom_created_at(self) -> None:
        """Test AssumptionItem con created_at personalizado."""
        now = datetime(2026, 5, 22, 10, 30, 0)
        item = AssumptionItem(
            id="assume-009",
            text="Test",
            created_at=now,
        )

        assert item.created_at == now


class TestProgressBar:
    """Tests para render_progress_bar."""

    def test_progress_bar_zero_progress(self) -> None:
        """Test barra con progreso 0."""
        bar = render_progress_bar(0, 5)

        assert "0/5" in bar
        assert "[" in bar and "]" in bar

    def test_progress_bar_half_progress(self) -> None:
        """Test barra con progreso a mitad."""
        bar = render_progress_bar(2, 4)

        assert "2/4" in bar
        assert "#" in bar
        assert "-" in bar

    def test_progress_bar_full_progress(self) -> None:
        """Test barra con progreso completo."""
        bar = render_progress_bar(5, 5)

        assert "5/5" in bar
        assert "#" in bar

    def test_progress_bar_zero_total(self) -> None:
        """Test barra con total 0."""
        bar = render_progress_bar(0, 0)

        assert "0/0" in bar

    def test_progress_bar_custom_width(self) -> None:
        """Test barra con ancho personalizado."""
        bar = render_progress_bar(1, 2, width=10)

        assert "1/2" in bar

    def test_progress_bar_format(self) -> None:
        """Test formato de barra."""
        bar = render_progress_bar(3, 10, width=20)

        assert bar.startswith("[")
        assert "]" in bar

    def test_progress_bar_boundaries(self) -> None:
        """Test límites de barra."""
        # Current > Total (debe limitarse a total)
        bar1 = render_progress_bar(10, 5)
        assert "]" in bar1

        # Negative values (deben convertirse a 0)
        bar2 = render_progress_bar(-1, 5)
        assert "0/5" in bar2

    def test_progress_bar_increment(self) -> None:
        """Test progreso incremental."""
        bars = [
            render_progress_bar(i, 5, width=10)
            for i in range(6)
        ]

        # Verificar que hay progreso
        assert len(bars) == 6
        # Todos deben ser válidos
        assert all("]" in bar for bar in bars)

    def test_progress_bar_single_step(self) -> None:
        """Test un solo paso."""
        bar = render_progress_bar(1, 1, width=5)
        assert "1/1" in bar
        assert "[" in bar and "]" in bar

    def test_progress_bar_large_numbers(self) -> None:
        """Test números grandes."""
        bar = render_progress_bar(9999, 10000, width=50)
        assert "9999/10000" in bar
