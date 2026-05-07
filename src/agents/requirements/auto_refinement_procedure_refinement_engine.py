
"""procedure_refinement_engine.py

Implementación del motor de auto-refinamiento para SDLAS.

Objetivo:
- Medir rendimiento de habilidades (SkillRecord)
- Recibir feedback externo
- Detectar degradación
- Generar acciones de mejora (RefinementAction)
- Auto-aplicar acciones seguras

No requiere dependencias externas.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .auto_refinement_models import SkillRecord, RefinementAction

logger = logging.getLogger(__name__)


class ProcedureRefinementEngine:
    """Engine that automatically refines agent procedures and skills."""

    def __init__(self, config: Optional[Dict[str, Any]] = None, decision_engine: Any = None) -> None:
        self._config = config or {}
        self._decision_engine = decision_engine

        self._skills: Dict[str, SkillRecord] = {}
        self._refinement_history: List[RefinementAction] = []
        self._feedback_buffer: List[Dict[str, Any]] = []

        self._ambiguity_patterns: Dict[str, int] = {}
        self._extraction_patterns: Dict[str, float] = {}

        self._refinement_threshold: float = float(self._config.get("refinement_threshold", 0.70))
        self._max_history: int = int(self._config.get("max_history", 500))
        self._safe_auto_apply: List[str] = list(self._config.get(
            "safe_auto_apply",
            ["add_heuristic", "add_validation", "optimize_pipeline"],
        ))

    # 1)
    def record_execution(self, skill_name: str, success: bool, execution_time: float, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Records execution metrics for a skill."""
        skill = self._ensure_skill(skill_name)
        skill.executions += 1
        if success:
            skill.successes += 1
        else:
            skill.failures += 1
        self._update_skill_timing(skill, float(execution_time))
        skill.last_executed = datetime.now()
        if metadata:
            # almacenar solo señales mínimas, no datos sensibles
            self._feedback_buffer.append({
                "skill_name": skill_name,
                "kind": "execution",
                "success": bool(success),
                "execution_time": float(execution_time),
                "timestamp": datetime.now().isoformat(),
                "metadata": dict(metadata),
            })
            self._trim_history()

    # 2)
    def record_feedback(self, skill_name: str, score: float, details: Optional[str] = None) -> None:
        """Records external feedback (from user or other agents)."""
        skill = self._ensure_skill(skill_name)
        score = max(0.0, min(1.0, float(score)))
        skill.last_feedback_score = score
        if details:
            skill.improvement_notes.append(details)
        self._feedback_buffer.append({
            "skill_name": skill_name,
            "kind": "feedback",
            "score": score,
            "details": details or "",
            "timestamp": datetime.now().isoformat(),
        })
        self._trim_history()

    # 3)
    def analyze_performance(self, skill_name: Optional[str] = None) -> Dict[str, Any]:
        """Analyzes performance of one or all skills, returns stats + recommendations."""
        targets = {skill_name: self._skills[skill_name]} if (skill_name and skill_name in self._skills) else self._skills
        report: Dict[str, Any] = {"skills": {}, "recommendations": []}
        for name, skill in targets.items():
            health = self._calculate_skill_health(skill)
            degradations = self._detect_degradation(skill)
            report["skills"][name] = {
                "executions": skill.executions,
                "success_rate": round(skill.success_rate, 4),
                "failure_rate": round(skill.failure_rate, 4),
                "avg_execution_time": round(skill.avg_execution_time, 4),
                "last_feedback_score": skill.last_feedback_score,
                "health": round(health, 4),
                "degradations": degradations,
            }
            if degradations or health < self._refinement_threshold:
                report["recommendations"].append({
                    "skill": name,
                    "health": round(health, 4),
                    "degradations": degradations,
                })
        return report

    # 4)
    def _detect_degradation(self, skill: SkillRecord) -> List[str]:
        """Detects if a skill is degrading (success rate dropping, time increasing)."""
        issues: List[str] = []
        if skill.executions >= 5 and skill.success_rate < self._refinement_threshold:
            issues.append(f"Tasa de éxito baja: {skill.success_rate:.0%}")
        if skill.avg_execution_time > float(self._config.get("max_avg_time", 10.0)):
            issues.append(f"Tiempo promedio alto: {skill.avg_execution_time:.2f}s")
        if 0 < skill.last_feedback_score < float(self._config.get("min_feedback", 0.60)):
            issues.append(f"Feedback bajo: {skill.last_feedback_score:.2f}")
        if skill.failures > skill.successes and skill.executions >= 5:
            issues.append("Más fallos que éxitos")
        return issues

    # 5)
    def generate_refinements(self) -> List[RefinementAction]:
        """Generates refinement actions based on analysis."""
        actions: List[RefinementAction] = []
        for name, skill in self._skills.items():
            health = self._calculate_skill_health(skill)
            miss_rate = skill.failure_rate

            # reglas solicitadas (heurísticas)
            if "ambigu" in name or "analyze" in name:
                if miss_rate > 0.30:
                    actions.append(self._make_action(
                        name,
                        "add_heuristic",
                        "Miss rate de ambigüedad > 30%: agregar patrones de términos vagos.",
                        0.7,
                    ))
            if "gather" in name or "extract" in name:
                if health < self._refinement_threshold:
                    actions.append(self._make_action(
                        name,
                        "adjust_prompt",
                        "Calidad de extracción degradada: sugerir refinamiento de prompt/plantilla.",
                        0.8,
                    ))
            if "validate" in name:
                if health < 0.6:
                    actions.append(self._make_action(
                        name,
                        "add_validation",
                        "Validación potencialmente estricta/laxa: ajustar umbrales y reglas.",
                        0.6,
                    ))
            # tipos que fallan sistemáticamente
            if miss_rate > 0.50 and skill.executions >= 5:
                actions.append(self._make_action(
                    name,
                    "optimize_pipeline",
                    "Fallo recurrente: añadir manejo especializado / reordenar pipeline.",
                    0.7,
                ))
            if health < 0.30 and skill.executions >= 10:
                actions.append(self._make_action(
                    name,
                    "escalate",
                    "Salud crítica: escalar a revisión humana.",
                    0.9,
                ))

        self._refinement_history.extend(actions)
        self._trim_history()
        return actions

    # 6)
    def apply_refinement(self, action_id: str) -> bool:
        """Marks a refinement as applied and updates internal state."""
        for action in self._refinement_history:
            if action.id == action_id and not action.applied:
                action.applied = True
                # efecto colateral: si es heurística de ambigüedad, añade tokens genéricos
                if action.action_type == "add_heuristic":
                    for t in ("etc.", "aprox.", "alrededor", "similar"):
                        self._ambiguity_patterns[t] = self._ambiguity_patterns.get(t, 0) + 1
                return True
        return False

    # 7)
    def learn_ambiguity_pattern(self, term: str, context: Optional[str] = None) -> None:
        """Learns a new ambiguity pattern from feedback."""
        t = (term or "").strip().lower()
        if not t:
            return
        self._ambiguity_patterns[t] = self._ambiguity_patterns.get(t, 0) + 1

    # 8)
    def learn_extraction_pattern(self, pattern_type: str, quality_score: float) -> None:
        """Learns extraction quality for different project types."""
        p = (pattern_type or "general").strip().lower()
        q = max(0.0, min(1.0, float(quality_score)))
        prev = self._extraction_patterns.get(p, q)
        self._extraction_patterns[p] = 0.7 * prev + 0.3 * q

    # 9)
    def get_learned_patterns(self) -> Dict[str, Any]:
        """Returns all learned patterns."""
        return {
            "ambiguity_patterns": dict(self._ambiguity_patterns),
            "extraction_patterns": dict(self._extraction_patterns),
        }

    # 10)
    def get_skill_summary(self) -> Dict[str, Any]:
        """Returns summary of all skills with recommendations."""
        summary: Dict[str, Any] = {"skills": {}, "avg_health": 0.0}
        healths: List[float] = []
        for name, skill in self._skills.items():
            h = self._calculate_skill_health(skill)
            healths.append(h)
            summary["skills"][name] = {
                "executions": skill.executions,
                "success_rate": round(skill.success_rate, 4),
                "avg_execution_time": round(skill.avg_execution_time, 4),
                "health": round(h, 4),
                "last_feedback": skill.last_feedback_score,
                "notes": skill.improvement_notes[-5:],
            }
        summary["avg_health"] = round(sum(healths) / len(healths), 4) if healths else 0.0
        return summary

    # 11)
    def auto_refine(self) -> List[RefinementAction]:
        """Full auto-refinement cycle: analyze -> generate -> apply safe refinements."""
        _ = self.analyze_performance()
        actions = self.generate_refinements()
        applied: List[RefinementAction] = []
        for a in actions:
            if self._should_auto_apply(a):
                if self.apply_refinement(a.id):
                    applied.append(a)
        return applied

    # 12)
    def _calculate_skill_health(self, skill: SkillRecord) -> float:
        """Returns 0-1 health score for a skill."""
        if skill.executions == 0:
            return 1.0
        success_component = skill.success_rate * 0.50
        time_penalty = min(skill.avg_execution_time / 30.0, 1.0)
        time_component = (1.0 - time_penalty) * 0.20
        feedback = skill.last_feedback_score if skill.last_feedback_score > 0 else skill.success_rate
        feedback_component = feedback * 0.30
        return max(0.0, min(1.0, success_component + time_component + feedback_component))

    # 13)
    def _should_auto_apply(self, action: RefinementAction) -> bool:
        """Determines if a refinement is safe to auto-apply."""
        if action.action_type == "escalate":
            return False
        return (action.action_type in self._safe_auto_apply) and (action.impact_score <= 0.8)

    # 14)
    def export_learnings(self) -> Dict[str, Any]:
        """Exports all learned data for persistence."""
        return {
            "skills": {k: v.to_dict() for k, v in self._skills.items()},
            "refinement_history": [a.to_dict() for a in self._refinement_history[-200:]],
            "feedback_buffer": list(self._feedback_buffer[-200:]),
            "ambiguity_patterns": dict(self._ambiguity_patterns),
            "extraction_patterns": dict(self._extraction_patterns),
            "exported_at": datetime.now().isoformat(),
        }

    # 15)
    def import_learnings(self, data: Dict[str, Any]) -> None:
        """Imports previously saved learnings."""
        skills = data.get("skills", {}) or {}
        for name, sdict in skills.items():
            self._skills[name] = SkillRecord.from_dict(sdict)
        self._ambiguity_patterns.update(data.get("ambiguity_patterns", {}) or {})
        self._extraction_patterns.update(data.get("extraction_patterns", {}) or {})
        for a in data.get("refinement_history", []) or []:
            try:
                self._refinement_history.append(RefinementAction.from_dict(a))
            except Exception:
                continue
        self._trim_history()

    # 16)
    def _ensure_skill(self, skill_name: str) -> SkillRecord:
        """Helper: get or create SkillRecord."""
        return self._skills.setdefault(skill_name, SkillRecord(skill_name=skill_name))

    # 17)
    def _trim_history(self) -> None:
        """Helper: trim history buffers."""
        if len(self._refinement_history) > self._max_history:
            self._refinement_history = self._refinement_history[-self._max_history:]
        if len(self._feedback_buffer) > self._max_history:
            self._feedback_buffer = self._feedback_buffer[-self._max_history:]

    # 18)
    def _make_action(self, skill_name: str, action_type: str, description: str, impact_score: float) -> RefinementAction:
        """Helper: create a RefinementAction with defaults."""
        return RefinementAction(
            skill_name=skill_name,
            action_type=action_type,
            description=description,
            impact_score=float(impact_score),
        )

    # 19)
    def _update_skill_timing(self, skill: SkillRecord, execution_time: float) -> None:
        """Helper: update average execution time."""
        skill.total_execution_time += float(execution_time)
        skill.avg_execution_time = skill.total_execution_time / max(skill.executions, 1)
