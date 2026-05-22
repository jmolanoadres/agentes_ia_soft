"""
Configuración del Requirements Agent v2.0.
Variables de entorno con prefijo SDLAS_REQ_.
"""


from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class RequirementsConfig(BaseSettings):
    """Configuración centralizada del Requirements Agent."""

    model_config = SettingsConfigDict(
        env_prefix="SDLAS_REQ_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── LLM ──────────────────────────────────────
    llm_provider: str = Field(default="Gemini", description="Proveedor LLM")
    llm_model: str = Field(default="gemini-3.5-flash", description="Modelo LLM")
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=256)

    # ── Embeddings / Memoria vectorial ───────────
    embedding_model: str = Field(default="text-embedding-3-small")
    vector_db_path: str = Field(default="./data/requirements_vectordb")
    similarity_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    llm_api_key: str = "AIzaSyA-uoxxOcavw7zbMBVMBtXXa_T51v_orG0"

    # ── Análisis de requisitos ───────────────────
    ambiguity_threshold: float = Field(
        default=0.4,
        ge=0.0,
        le=1.0,
        description="Umbral sobre el cual un requisito se marca como ambiguo",
    )
    max_requirements_per_srs: int = Field(default=100, ge=1)
    min_acceptance_criteria: int = Field(default=2, ge=1)

    # ── Aprobación ───────────────────────────────
    auto_approve_threshold: float = Field(
        default=95.0, ge=0.0, le=100.0, description="Completeness score mínimo para auto-aprobación"
    )
    approval_timeout_seconds: int = Field(default=3600, ge=60)

    # ── Feature flags ────────────────────────────
    enable_memory: bool = Field(default=True)
    enable_llm: bool = Field(default=True)

    # ── Operacional ──────────────────────────────
    log_level: str = Field(default="INFO")
    max_retries: int = Field(default=3, ge=0)
    srs_output_format: str = Field(default="json")


# ── Singleton ────────────────────────────────────
_config_instance: RequirementsConfig | None = None


def get_config() -> RequirementsConfig:
    """Obtener instancia singleton de configuración."""
    global _config_instance
    if _config_instance is None:
        _config_instance = RequirementsConfig()
    return _config_instance
