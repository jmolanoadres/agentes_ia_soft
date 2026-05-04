"""
Motor LLM para el Requirements Agent v2.0.
Integración con LangChain + Fallback heurístico.
"""

from __future__ import annotations

import logging
import re
import uuid
from typing import Any, Dict, List, Optional

from .requirements_config import get_config
from .requirements_models import (
    AmbiguityFlag,
    AmbiguityReport,
    ComplexityLevel,
    PriorityLevel,
    Requirement,
    RequirementType,
    UseCase,
)

logger = logging.getLogger(__name__)

# ── Importar LangChain (con fallback) ──────────
try:
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import JsonOutputParser

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logger.warning("langchain no disponible. Usando motor heurístico.")


# ═══════════════════════════════════════════════
#  PROMPTS
# ═══════════════════════════════════════════════

EXTRACT_REQUIREMENTS_PROMPT = """Eres un analista de requisitos de software experto.
Analiza la siguiente descripción de proyecto y extrae requisitos estructurados.

Descripción del proyecto:
{project_description}

Devuelve un JSON con la siguiente estructura:
{{
    "requirements": [
        {{
            "title": "Título conciso del requisito",
            "description": "Descripción detallada (mínimo 30 palabras)",
            "req_type": "functional|non_functional|constraint|interface|security|performance",
            "priority": "must|should|could|wont",
            "acceptance_criteria": ["Criterio 1", "Criterio 2", "Criterio 3"],
            "risks": ["Riesgo identificado"],
            "assumptions": ["Supuesto"],
            "tags": ["tag1", "tag2"]
        }}
    ],
    "glossary": {{"término": "definición"}},
    "constraints": ["Restricción del sistema"],
    "assumptions": ["Supuesto general del proyecto"]
}}

IMPORTANTE:
- Cada requisito debe tener al menos 2 criterios de aceptación
- Incluye requisitos funcionales Y no funcionales
- Identifica restricciones de seguridad y rendimiento
- Sé específico, evita ambigüedades
"""

DETECT_AMBIGUITY_PROMPT = """Eres un experto en calidad de requisitos de software.
Analiza el siguiente requisito y detecta cualquier ambigüedad.

Requisito:
Título: {title}
Descripción: {description}
Criterios de aceptación: {acceptance_criteria}

Evalúa cada uno de estos tipos de ambigüedad:
- vague_term: Términos vagos (rápido, eficiente, fácil, óptimo, etc.)
- missing_metric: Falta de métricas cuantificables
- unclear_actor: Actor no definido claramente
- missing_boundary: Límites no especificados
- passive_voice: Voz pasiva que oculta responsabilidad
- multiple_interpretations: Texto con múltiples interpretaciones
- undefined_reference: Referencias a elementos no definidos

Devuelve JSON:
{{
    "flags": ["tipo_ambiguedad_1", "tipo_ambiguedad_2"],
    "details": ["Detalle específico de cada ambigüedad"],
    "score": 0.0 a 1.0 (0 = claro, 1 = muy ambiguo),
    "suggestions": ["Sugerencia de mejora 1", "Sugerencia 2"]
}}
"""

GENERATE_USE_CASES_PROMPT = """Eres un analista funcional experto.
Genera casos de uso detallados para los siguientes requisitos funcionales.

Requisitos:
{requirements_text}

Para cada requisito funcional, genera un caso de uso con:
{{
    "use_cases": [
        {{
            "name": "UC-NombreDescriptivo",
            "actor": "Actor principal",
            "description": "Descripción del caso de uso",
            "preconditions": ["Precondición 1"],
            "steps": ["1. Paso principal", "2. Siguiente paso"],
            "postconditions": ["Postcondición 1"],
            "alternative_flows": [
                {{"name": "Flujo alternativo", "steps": ["1. Paso"]}}
            ],
            "exception_flows": [
                {{"name": "Excepción", "steps": ["1. Paso"], "result": "Resultado"}}
            ],
            "related_requirements": ["req_id_1"]
        }}
    ]
}}
"""

GENERATE_CRITERIA_PROMPT = """Eres un analista QA experto.
Genera criterios de aceptación claros y verificables para este requisito:

Título: {title}
Descripción: {description}
Tipo: {req_type}

Devuelve JSON:
{{
    "acceptance_criteria": [
        "DADO [contexto] CUANDO [acción] ENTONCES [resultado esperado]"
    ]
}}

Genera al menos 3 criterios usando formato Gherkin (Given/When/Then).
"""

ESTIMATE_COMPLEXITY_PROMPT = """Eres un arquitecto de software senior.
Estima la complejidad de implementar este requisito:

Título: {title}
Descripción: {description}
Tipo: {req_type}
Dependencias: {dependencies}

Devuelve JSON:
{{
    "complexity": "trivial|low|medium|high|very_high",
    "estimated_hours": número,
    "factors": ["Factor que contribuye a la complejidad"],
    "risks": ["Riesgo técnico identificado"]
}}
"""


# ═══════════════════════════════════════════════
#  MOTOR LLM CON LANGCHAIN
# ═══════════════════════════════════════════════

class RequirementsLLMEngine:
    """
    Motor de análisis de requisitos basado en LLM.

    Si LangChain no está disponible, usa FallbackEngine.
    """

    def __init__(self, config=None):
        self._config = config or get_config()
        self._llm = None
        self._parser = None

        if LANGCHAIN_AVAILABLE and self._config.enable_llm:
            try:
                self._llm = ChatOpenAI(
                    model=self._config.llm_model,
                    temperature=self._config.temperature,
                    max_tokens=self._config.max_tokens,
                )
                self._parser = JsonOutputParser()
                logger.info(
                    f"LLM Engine inicializado: {self._config.llm_provider}/"
                    f"{self._config.llm_model}"
                )
            except Exception as e:
                logger.warning(f"Error inicializando LLM: {e}. Usando fallback.")
                self._llm = None

        if self._llm is None:
            logger.info("Usando FallbackLLMEngine (heurístico)")

    # ── Métodos principales ──────────────────────

    async def extract_requirements(
        self,
        project_description: str,
    ) -> Dict[str, Any]:
        """
        Extraer requisitos estructurados de una descripción.

        Returns:
            Dict con requirements, glossary, constraints, assumptions.
        """
        if self._llm:
            return await self._llm_extract(project_description)
        return self._fallback_extract(project_description)

    async def detect_ambiguity(
        self,
        requirement: Requirement,
    ) -> AmbiguityReport:
        """Analizar ambigüedad de un requisito."""
        if self._llm:
            return await self._llm_detect_ambiguity(requirement)
        return self._fallback_detect_ambiguity(requirement)

    async def generate_acceptance_criteria(
        self,
        requirement: Requirement,
    ) -> List[str]:
        """Generar criterios de aceptación para un requisito."""
        if self._llm:
            return await self._llm_generate_criteria(requirement)
        return self._fallback_generate_criteria(requirement)

    async def generate_use_cases(
        self,
        requirements: List[Requirement],
    ) -> List[UseCase]:
        """Generar casos de uso desde requisitos funcionales."""
        if self._llm:
            return await self._llm_generate_use_cases(requirements)
        return self._fallback_generate_use_cases(requirements)

    async def estimate_complexity(
        self,
        requirement: Requirement,
    ) -> Dict[str, Any]:
        """Estimar complejidad de un requisito."""
        if self._llm:
            return await self._llm_estimate_complexity(requirement)
        return self._fallback_estimate_complexity(requirement)

    async def classify_requirement(self, text: str) -> RequirementType:
        """Clasificar tipo de requisito desde texto libre."""
        text_lower = text.lower()
        nf_keywords = [
            "rendimiento", "performance", "seguridad", "security",
            "disponibilidad", "availability", "escalabilidad", "scalability",
            "usabilidad", "mantenibilidad", "confiabilidad",
        ]
        sec_keywords = ["autenticación", "autorización", "cifrado", "token", "ssl", "oauth"]
        perf_keywords = ["latencia", "throughput", "concurrencia", "tiempo de respuesta"]

        if any(k in text_lower for k in sec_keywords):
            return RequirementType.SECURITY
        if any(k in text_lower for k in perf_keywords):
            return RequirementType.PERFORMANCE
        if any(k in text_lower for k in nf_keywords):
            return RequirementType.NON_FUNCTIONAL
        return RequirementType.FUNCTIONAL

    # ── LLM implementations ──────────────────────

    async def _llm_extract(self, description: str) -> Dict[str, Any]:
        prompt = ChatPromptTemplate.from_template(EXTRACT_REQUIREMENTS_PROMPT)
        chain = prompt | self._llm | self._parser
        result = await chain.ainvoke({"project_description": description})
        return result

    async def _llm_detect_ambiguity(self, req: Requirement) -> AmbiguityReport:
        prompt = ChatPromptTemplate.from_template(DETECT_AMBIGUITY_PROMPT)
        chain = prompt | self._llm | self._parser
        result = await chain.ainvoke({
            "title": req.title,
            "description": req.description,
            "acceptance_criteria": "; ".join(req.acceptance_criteria),
        })
        return AmbiguityReport(
            flags=[AmbiguityFlag(f) for f in result.get("flags", [])
                   if f in [e.value for e in AmbiguityFlag]],
            details=result.get("details", []),
            score=result.get("score", 0.0),
            suggestions=result.get("suggestions", []),
        )

    async def _llm_generate_criteria(self, req: Requirement) -> List[str]:
        prompt = ChatPromptTemplate.from_template(GENERATE_CRITERIA_PROMPT)
        chain = prompt | self._llm | self._parser
        result = await chain.ainvoke({
            "title": req.title,
            "description": req.description,
            "req_type": req.req_type.value,
        })
        return result.get("acceptance_criteria", [])

    async def _llm_generate_use_cases(
        self, requirements: List[Requirement]
    ) -> List[UseCase]:
        functional = [r for r in requirements if r.req_type == RequirementType.FUNCTIONAL]
        if not functional:
            return []

        req_text = "\n".join(
            f"- [{r.id}] {r.title}: {r.description}" for r in functional
        )
        prompt = ChatPromptTemplate.from_template(GENERATE_USE_CASES_PROMPT)
        chain = prompt | self._llm | self._parser
        result = await chain.ainvoke({"requirements_text": req_text})

        use_cases = []
        for uc_data in result.get("use_cases", []):
            use_cases.append(UseCase(
                id=str(uuid.uuid4()),
                name=uc_data.get("name", ""),
                actor=uc_data.get("actor", "Usuario"),
                description=uc_data.get("description", ""),
                preconditions=uc_data.get("preconditions", []),
                steps=uc_data.get("steps", []),
                postconditions=uc_data.get("postconditions", []),
                alternative_flows=uc_data.get("alternative_flows", []),
                exception_flows=uc_data.get("exception_flows", []),
                related_requirements=uc_data.get("related_requirements", []),
            ))
        return use_cases

    async def _llm_estimate_complexity(self, req: Requirement) -> Dict[str, Any]:
        prompt = ChatPromptTemplate.from_template(ESTIMATE_COMPLEXITY_PROMPT)
        chain = prompt | self._llm | self._parser
        return await chain.ainvoke({
            "title": req.title,
            "description": req.description,
            "req_type": req.req_type.value,
            "dependencies": ", ".join(req.dependencies) or "Ninguna",
        })

    # ── Fallback heurístico ──────────────────────

    def _fallback_extract(self, description: str) -> Dict[str, Any]:
        """Extracción heurística basada en patrones."""
        sentences = [
            s.strip() for s in re.split(r"[.\n]", description)
            if len(s.strip()) > 15
        ]
        requirements = []
        for i, sentence in enumerate(sentences):
            req_type = self._classify_sentence(sentence)
            requirements.append({
                "title": self._generate_title(sentence),
                "description": sentence,
                "req_type": req_type.value,
                "priority": "should",
                "acceptance_criteria": [
                    f"El sistema cumple: {sentence[:80]}",
                    f"Se verifica mediante prueba automatizada",
                ],
                "risks": [],
                "assumptions": [],
                "tags": self._extract_tags(sentence),
            })
        return {
            "requirements": requirements,
            "glossary": {},
            "constraints": [],
            "assumptions": [],
        }

    def _fallback_detect_ambiguity(self, req: Requirement) -> AmbiguityReport:
        """Detección heurística de ambigüedad."""
        VAGUE_TERMS = {
            "rápido", "rápida", "eficiente", "fácil", "simple",
            "óptimo", "adecuado", "apropiado", "suficiente",
            "bueno", "mejor", "correcto", "seguro", "robusto",
            "flexible", "amigable", "intuitivo", "moderno",
            "fast", "efficient", "easy", "optimal", "good",
            "appropriate", "secure", "robust", "user-friendly",
        }

        flags = []
        details = []
        suggestions = []
        text = f"{req.title} {req.description}".lower()
        words = set(text.split())

        # Verificar términos vagos
        found_vague = words & VAGUE_TERMS
        if found_vague:
            flags.append(AmbiguityFlag.VAGUE_TERM)
            for term in found_vague:
                details.append(f"Término vago detectado: '{term}'")
                suggestions.append(
                    f"Reemplazar '{term}' con una métrica específica "
                    f"(ej: 'tiempo de respuesta < 2s' en lugar de 'rápido')"
                )

        # Verificar métricas ausentes
        has_numbers = bool(re.search(r"\d+", text))
        if req.req_type in (
            RequirementType.PERFORMANCE,
            RequirementType.NON_FUNCTIONAL,
        ) and not has_numbers:
            flags.append(AmbiguityFlag.MISSING_METRIC)
            details.append("Requisito no funcional sin métricas cuantificables")
            suggestions.append("Agregar métricas específicas (tiempos, porcentajes, etc.)")

        # Verificar voz pasiva
        passive_patterns = [
            r"\bse debe\b", r"\bdebe ser\b", r"\bes requerido\b",
            r"\bshould be\b", r"\bmust be\b",
        ]
        if any(re.search(p, text) for p in passive_patterns):
            flags.append(AmbiguityFlag.PASSIVE_VOICE)
            details.append("Uso de voz pasiva detectado")
            suggestions.append("Usar voz activa: 'El sistema DEBE [verbo] ...'")

        # Verificar actor ausente
        actor_keywords = [
            "usuario", "admin", "sistema", "cliente", "operador",
            "user", "admin", "system", "client", "operator",
        ]
        if not any(k in text for k in actor_keywords):
            flags.append(AmbiguityFlag.UNCLEAR_ACTOR)
            details.append("No se identifica un actor claro")
            suggestions.append("Especificar quién realiza la acción")

        # Calcular score
        score = min(len(flags) * 0.2, 1.0)

        return AmbiguityReport(
            flags=flags,
            details=details,
            score=score,
            suggestions=suggestions,
        )

    def _fallback_generate_criteria(self, req: Requirement) -> List[str]:
        """Generar criterios básicos heurísticamente."""
        criteria = [
            f"DADO que el usuario está autenticado "
            f"CUANDO solicita {req.title.lower()} "
            f"ENTONCES el sistema ejecuta la operación exitosamente",
            f"DADO una solicitud válida "
            f"CUANDO se procesa {req.title.lower()} "
            f"ENTONCES el sistema responde en menos de 2 segundos",
            f"DADO una solicitud inválida "
            f"CUANDO se intenta {req.title.lower()} "
            f"ENTONCES el sistema muestra un mensaje de error descriptivo",
        ]
        return criteria

    def _fallback_generate_use_cases(
        self, requirements: List[Requirement]
    ) -> List[UseCase]:
        """Generar casos de uso básicos heurísticamente."""
        use_cases = []
        for req in requirements:
            if req.req_type != RequirementType.FUNCTIONAL:
                continue
            uc = UseCase(
                id=str(uuid.uuid4()),
                name=f"UC-{req.title.replace(' ', '_')[:30]}",
                actor="Usuario",
                description=req.description,
                preconditions=["Usuario autenticado en el sistema"],
                steps=[
                    f"1. El usuario solicita: {req.title}",
                    "2. El sistema valida la solicitud",
                    "3. El sistema procesa la operación",
                    "4. El sistema confirma el resultado al usuario",
                ],
                postconditions=["Operación completada", "Datos actualizados"],
                alternative_flows=[{
                    "name": "Datos incompletos",
                    "steps": [
                        "2a. El sistema detecta datos faltantes",
                        "2b. El sistema solicita la información necesaria",
                    ],
                }],
                exception_flows=[{
                    "name": "Error del sistema",
                    "steps": [
                        "3a. Ocurre un error durante el procesamiento",
                        "3b. El sistema registra el error y notifica al usuario",
                    ],
                    "result": "El usuario recibe un mensaje de error",
                }],
                related_requirements=[req.id],
                priority=req.priority,
            )
            use_cases.append(uc)
        return use_cases

    def _fallback_estimate_complexity(self, req: Requirement) -> Dict[str, Any]:
        """Estimación heurística de complejidad."""
        score = 0
        desc_len = len(req.description)
        if desc_len > 200:
            score += 2
        elif desc_len > 100:
            score += 1
        score += len(req.dependencies)
        score += len(req.acceptance_criteria)
        if req.req_type in (RequirementType.SECURITY, RequirementType.PERFORMANCE):
            score += 2

        if score <= 2:
            level = "simple"
            hours = 4
        elif score <= 5:
            level = "medium"
            hours = 16
        elif score <= 8:
            level = "high"
            hours = 40
        else:
            level = "very_high"
            hours = 80

        return {
            "complexity": level,
            "estimated_hours": hours,
            "factors": [
                f"Longitud de descripción: {desc_len} chars",
                f"Dependencias: {len(req.dependencies)}",
                f"Criterios de aceptación: {len(req.acceptance_criteria)}",
                f"Tipo: {req.req_type.value}",
            ],
            "risks": req.risks or ["Sin riesgos técnicos identificados"],
        }

    # ── Utilidades internas ──────────────────────

    def _classify_sentence(self, sentence: str) -> RequirementType:
        s = sentence.lower()
        if any(k in s for k in ["seguridad", "autenticación", "cifrado"]):
            return RequirementType.SECURITY
        if any(k in s for k in ["rendimiento", "latencia", "velocidad"]):
            return RequirementType.PERFORMANCE
        if any(k in s for k in ["debe cumplir", "restricción", "limitación"]):
            return RequirementType.CONSTRAINT
        return RequirementType.FUNCTIONAL

    @staticmethod
    def _generate_title(sentence: str) -> str:
        words = sentence.split()[:8]
        title = " ".join(words)
        if len(title) > 60:
            title = title[:57] + "..."
        return title

    @staticmethod
    def _extract_tags(sentence: str) -> List[str]:
        tag_patterns = {
            "api": ["api", "endpoint", "rest", "graphql"],
            "auth": ["autenticación", "login", "sesión", "token"],
            "database": ["base de datos", "almacenamiento", "persistencia"],
            "ui": ["interfaz", "pantalla", "formulario", "vista"],
            "integration": ["integración", "webhook", "evento"],
        }
        tags = []
        s = sentence.lower()
        for tag, keywords in tag_patterns.items():
            if any(k in s for k in keywords):
                tags.append(tag)
        return tags