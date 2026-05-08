
"""requirements_assumptions.py

Módulo de revisión interactiva de supuestos (assumptions).

Objetivo:
- Listar los supuestos que el agente está asumiendo.
- Permitir al usuario seleccionar cuáles no le gustan (por número) o elegir "otra".
- Preguntar uno a uno la redefinición de los supuestos rechazados.
- Mostrar una barra de progreso en cada pregunta.

Este módulo NO depende de herramientas externas. Se integra con RequirementsAgentV2.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class AssumptionItem:
    """Elemento de supuesto (assumption) con estado."""

    id: str
    text: str
    status: str = "assumed"  # assumed | accepted | rejected | redefined | added
    user_definition: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "status": self.status,
            "user_definition": self.user_definition,
            "created_at": self.created_at.isoformat(),
        }


def render_progress_bar(current: int, total: int, width: int = 24) -> str:
    """Devuelve una barra de progreso textual: [####------] 2/5"""
    total = max(0, int(total))
    current = max(0, min(int(current), total if total else 0))
    if total == 0:
        return "[" + ("#" * width) + "] 0/0"
    filled = int(round(width * (current / total)))
    return "[" + ("#" * filled) + ("-" * (width - filled)) + f"] {current}/{total}"


class AssumptionReviewSession:
    """Sesión de revisión de supuestos.

    Flujo:
        1) start() -> devuelve lista numerada + opción 'otra'
        2) apply_selection(user_input) -> define qué supuestos se redefinen
        3) answer_current(answer) -> guarda respuesta y avanza
        4) cuando termina -> ready_for_spec=True

    La sesión es determinista y serializable.
    """

    def __init__(self, assumptions: List[str]) -> None:
        self.session_id: str = str(uuid.uuid4())
        self.items: List[AssumptionItem] = [
            AssumptionItem(id=str(uuid.uuid4()), text=a.strip())
            for a in assumptions
            if a and a.strip()
        ]
        self.other_item: AssumptionItem = AssumptionItem(
            id=str(uuid.uuid4()),
            text="Otra (especificar un supuesto adicional)",
            status="assumed",
        )
        self.items.append(self.other_item)

        self.selected_indexes: List[int] = []  # índices a redefinir (1-based)
        self.questions: List[int] = []         # cola de índices (1-based)
        self.current_question_pos: int = 0
        self.started: bool = False
        self.completed: bool = False

    @property
    def other_index(self) -> int:
        return len(self.items)  # siempre último (1-based)

    def start(self) -> Dict[str, Any]:
        self.started = True
        return {
            "session_id": self.session_id,
            "stage": "assumptions_list",
            "instructions": (
                "Estos son los supuestos que el agente está asumiendo. "
                "Indica los NÚMEROS de los supuestos que NO te gustan, separados por coma. "
                "Ejemplo: 2,5,7. Si todos están bien, responde 0. "
                "Si quieres agregar uno nuevo, incluye el número de 'Otra'."
            ),
            "assumptions": self._render_list(),
            "other_index": self.other_index,
        }

    def apply_selection(self, user_input: str) -> Dict[str, Any]:
        if not self.started:
            return self.start()

        selection = self._parse_selection(user_input)
        self.selected_indexes = selection

        # Marcar aceptados/rechazados preliminares
        for i, item in enumerate(self.items, start=1):
            if i in selection:
                item.status = "rejected"
            else:
                item.status = "accepted"

        # Preparar preguntas (en el orden seleccionado)
        self.questions = list(selection)
        self.current_question_pos = 0

        if not self.questions:
            self.completed = True
            return {
                "session_id": self.session_id,
                "stage": "assumptions_done",
                "ready_for_spec": True,
                "message": "Perfecto. Todos los supuestos fueron aceptados. Ya estoy listo para crear la especificación.",
                "assumptions": self._render_list(show_status=True),
            }

        # primera pregunta
        return self._next_question_payload()

    def answer_current(self, answer: str) -> Dict[str, Any]:
        if self.completed:
            return {
                "session_id": self.session_id,
                "stage": "assumptions_done",
                "ready_for_spec": True,
                "message": "Ya estoy listo para crear la especificación.",
                "assumptions": self._render_list(show_status=True),
            }

        if not self.questions:
            return self.apply_selection("0")

        idx = self.questions[self.current_question_pos]
        item = self.items[idx - 1]

        # Caso 'Otra'
        if idx == self.other_index:
            item.status = "added"
            item.user_definition = (answer or "").strip()
            if item.user_definition:
                item.text = f"Otra: {item.user_definition}"
        else:
            item.status = "redefined"
            item.user_definition = (answer or "").strip()
            if item.user_definition:
                item.text = item.user_definition

        # avanzar
        self.current_question_pos += 1
        if self.current_question_pos >= len(self.questions):
            self.completed = True
            return {
                "session_id": self.session_id,
                "stage": "assumptions_done",
                "ready_for_spec": True,
                "message": "Gracias. Ya me encuentro listo para crear la especificación.",
                "assumptions": self._render_list(show_status=True),
            }

        return self._next_question_payload()

    # ------------------------ helpers ------------------------

    def _next_question_payload(self) -> Dict[str, Any]:
        total = len(self.questions)
        current = self.current_question_pos + 1
        idx = self.questions[self.current_question_pos]
        item = self.items[idx - 1]

        progress = render_progress_bar(current - 1, total)

        if idx == self.other_index:
            question = "Has seleccionado 'Otra'. Especifica el supuesto adicional que deseas incluir:" 
        else:
            question = (
                f"Redefine el supuesto #{idx}: '{item.text}'. "
                "Escribe la nueva definición (clara y verificable):"
            )

        return {
            "session_id": self.session_id,
            "stage": "assumption_question",
            "progress": progress,
            "question_number": current,
            "questions_total": total,
            "question": question,
            "assumptions": self._render_list(show_status=True, mark_other=True),
            "note": "En la lista, el último ítem es la opción 'Otra'.",
        }

    def _render_list(self, show_status: bool = False, mark_other: bool = False) -> List[str]:
        out: List[str] = []
        for i, item in enumerate(self.items, start=1):
            suffix = ""
            if show_status:
                suffix = f"  [{item.status}]"
            if mark_other and i == self.other_index:
                suffix += "  (otra)"
            out.append(f"{i}. {item.text}{suffix}")
        return out

    def _parse_selection(self, user_input: str) -> List[int]:
        s = (user_input or "").strip().lower()
        if s in ("0", "", "ninguna", "ninguno", "todo", "ok"):
            return []

        # permitir que el usuario escriba 'otra'
        if s == "otra":
            return [self.other_index]

        # parse coma/espacios
        nums: List[int] = []
        for part in s.replace(";", ",").split(","):
            p = part.strip()
            if not p:
                continue
            if p == "otra":
                nums.append(self.other_index)
                continue
            try:
                n = int(p)
                if 1 <= n <= len(self.items):
                    nums.append(n)
            except Exception:
                continue

        # unique preserving order
        seen = set()
        ordered = []
        for n in nums:
            if n not in seen:
                ordered.append(n)
                seen.add(n)

        return ordered
