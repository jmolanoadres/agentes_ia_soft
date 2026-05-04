"""
Requirements Agent v2.0 — Paquete principal.
Sistema Multiagente SDLAS.
"""

from .requirements_config import RequirementsConfig, get_config
from .requirements_models import (
    Requirement, UseCase, SoftwareRequirementsSpec,
    RequirementChange, SRSVersion, TraceabilityEntry,
    TraceabilityMatrix, ApprovalRequest, ApprovalResponse,
    DesignHandoffPackage, AmbiguityReport, AmbiguityFlag,
    RequirementType, RequirementStatus, PriorityLevel,
    ComplexityLevel, ApprovalStatus,
)
from .requirements_memory import RequirementsMemory
from .requirements_llm import RequirementsLLMEngine
from .requirements_flow import RequirementsWorkflow, ApprovalGate
from .requirements_agent_v2 import RequirementsAgentV2

__all__ = [
    "RequirementsAgentV2",
    "RequirementsConfig",
    "RequirementsMemory",
    "RequirementsLLMEngine",
    "RequirementsWorkflow",
    "ApprovalGate",
    "Requirement",
    "UseCase",
    "SoftwareRequirementsSpec",
    "DesignHandoffPackage",
    "TraceabilityMatrix",
    "ApprovalRequest",
    "ApprovalResponse",
]