"""Code agent for implementation and code generation."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from src.agents.base.base_agent import BaseAgent, AgentState, Task, TaskResult, TaskStatus, Capability

logger = logging.getLogger(__name__)


@dataclass
class CodeModule:
    """Módulo de código generado."""
    id: str
    name: str
    file_path: str
    content: str
    language: str
    imports: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class CodeArtifact:
    """Artefacto de código (clase, función, etc.)."""
    name: str
    type: str  # class, function, module
    content: str
    docstring: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)


class CodeBackendAgent(BaseAgent):
    """Agente especializado en generación de código backend."""
    
    def __init__(self):
        super().__init__(
            agent_id="code_backend",
            name="Code Backend Agent",
            description="Agente para implementación de código backend (Python, FastAPI, etc.)"
        )
        self._generated_modules: Dict[str, CodeModule] = {}
        self._code_templates = self._load_templates()
        
        self._register_capabilities()
    
    def _register_capabilities(self) -> None:
        """Registrar las capacidades del agente."""
        self.add_capability(Capability(
            name="generate_code",
            description="Generar código fuente",
            version="1.0.0"
        ))
        self.add_capability(Capability(
            name="refactor_code",
            description="Refactorizar código existente",
            version="1.0.0"
        ))
        self.add_capability(Capability(
            name="apply_standards",
            description="Aplicar estándares de codificación",
            version="1.0.0"
        ))
        self.add_capability(Capability(
            name="generate_documentation",
            description="Generar documentación de código",
            version="1.0.0"
        ))
        self.add_capability(Capability(
            name="manage_dependencies",
            description="Gestionar dependencias del proyecto",
            version="1.0.0"
        ))
    
    def _load_templates(self) -> Dict[str, str]:
        """Cargar plantillas de código."""
        return {
            "fastapi_model": '''from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class {class_name}Base(BaseModel):
    """Base model for {class_name}."""
    pass


class {class_name}Create({class_name}Base):
    """Model for creating {class_name}."""
    pass


class {class_name}Update(BaseModel):
    """Model for updating {class_name}."""
    pass


class {class_name}Response({class_name}Base):
    """Model for {class_name} response."""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
''',
            "fastapi_route": '''from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from {model_import} import {model_name}Response, {model_name}Create, {model_name}Update
from {service_import} import {service_name}


router = APIRouter(prefix="/{entity}", tags=["{entity}"])


def get_{service_var}({service_var}: {service_name} = Depends()) -> {service_name}:
    """Get {service_name} instance."""
    return {service_var}


@router.get("", response_model=List[{model_name}Response])
async def list_{entity}(
    {service_var}: {service_name} = Depends(get_{service_var}),
    skip: int = 0,
    limit: int = 100
):
    """List all {entity}."""
    return await {service_var}.list(skip=skip, limit=limit)


@router.get("/{entity}_id", response_model={model_name}Response)
async def get_{entity}(
    {entity}_id: int,
    {service_var}: {service_name} = Depends(get_{service_var})
):
    """Get {entity} by ID."""
    result = await {service_var}.get({entity}_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return result


@router.post("", response_model={model_name}Response, status_code=status.HTTP_201_CREATED)
async def create_{entity}(
    data: {model_name}Create,
    {service_var}: {service_name} = Depends(get_{service_var})
):
    """Create new {entity}."""
    return await {service_var}.create(data)


@router.put("/{entity}_id", response_model={model_name}Response)
async def update_{entity}(
    {entity}_id: int,
    data: {model_name}Update,
    {service_var}: {service_name} = Depends(get_{service_var})
):
    """Update {entity}."""
    result = await {service_var}.update({entity}_id, data)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return result


@router.delete("/{entity}_id", status_code=status.HTTP_204_NO_CONTENT)
async def delete_{entity}(
    {entity}_id: int,
    {service_var}: {service_name} = Depends(get_{service_var})
):
    """Delete {entity}."""
    result = await {service_var}.delete({entity}_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return None
''',
            "service": '''from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from {model_import} import {model_name}


class {service_name}:
    """Service for {entity} operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def list(self, skip: int = 0, limit: int = 100) -> List[{model_name}]:
        """List {entity} with pagination."""
        result = await self.db.execute(
            select({model_name}).offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    async def get(self, id: int) -> Optional[{model_name}]:
        """Get {entity} by ID."""
        result = await self.db.execute(
            select({model_name}).where({model_name}.id == id)
        )
        return result.scalar_one_or_none()
    
    async def create(self, data) -> {model_name}:
        """Create new {entity}."""
        db_obj = {model_name}(**data.model_dump())
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj
    
    async def update(self, id: int, data) -> Optional[{model_name}]:
        """Update {entity}."""
        obj = await self.get(id)
        if obj:
            for key, value in data.model_dump(exclude_unset=True).items():
                setattr(obj, key, value)
            await self.db.commit()
            await self.db.refresh(obj)
        return obj
    
    async def delete(self, id: int) -> bool:
        """Delete {entity}."""
        obj = await self.get(id)
        if obj:
            await self.db.delete(obj)
            await self.db.commit()
            return True
        return False
''',
            "sqlalchemy_model": '''from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import declarative_base
from datetime import datetime


Base = declarative_base()


class {class_name}(Base):
    """SQLAlchemy model for {class_name}."""
    
    __tablename__ = "{table_name}"
    
    id = Column(Integer, primary_key=True, index=True)
    # Add columns here
    
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
'''
        }
    
    async def initialize(self) -> None:
        """Inicializar el agente."""
        self.update_state(AgentState.INITIALIZING)
        logger.info(f"Initializing {self._name}")
        self.update_state(AgentState.IDLE)
    
    async def execute(self, task: Task) -> TaskResult:
        """Ejecutar una tarea de código."""
        start_time = datetime.now()
        self.update_state(AgentState.PROCESSING)
        
        try:
            task_type = task.type
            
            if task_type == "generate_code":
                result = await self._generate_code(task.input_data)
            elif task_type == "refactor_code":
                result = await self._refactor_code(task.input_data)
            elif task_type == "apply_standards":
                result = await self._apply_standards(task.input_data)
            elif task_type == "generate_documentation":
                result = await self._generate_documentation(task.input_data)
            elif task_type == "manage_dependencies":
                result = await self._manage_dependencies(task.input_data)
            else:
                raise ValueError(f"Unknown task type: {task_type}")
            
            execution_time = (datetime.now() - start_time).total_seconds()
            self.update_metrics(execution_time, success=True)
            self.update_state(AgentState.IDLE)
            
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                output_data=result,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.update_metrics(execution_time, success=False)
            self.update_state(AgentState.ERROR)
            logger.error(f"Error executing task: {e}")
            
            return TaskResult(
                task_id=task.id,
                status=TaskStatus.FAILED,
                error=str(e),
                execution_time=execution_time
            )
    
    async def _generate_code(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generar código fuente."""
        entity_name = input_data.get("entity_name", "Entity")
        framework = input_data.get("framework", "fastapi")
        modules = input_data.get("modules", ["model", "schema", "service", "route"])
        
        generated = {}
        
        for module in modules:
            if module == "model":
                content = self._generate_model(entity_name)
            elif module == "schema":
                content = self._generate_schema(entity_name)
            elif module == "service":
                content = self._generate_service(entity_name)
            elif module == "route":
                content = self._generate_route(entity_name)
            else:
                continue
            
            module_obj = CodeModule(
                id=str(uuid.uuid4()),
                name=f"{entity_name}_{module}",
                file_path=f"src/{entity_name.lower()}/{module}.py",
                content=content,
                language="python",
                imports=self._extract_imports(content)
            )
            
            self._generated_modules[module_obj.id] = module_obj
            generated[module] = {
                "file_path": module_obj.file_path,
                "content": content
            }
        
        return {
            "entity_name": entity_name,
            "framework": framework,
            "modules": generated,
            "count": len(generated)
        }
    
    async def _refactor_code(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Refactorizar código existente."""
        code = input_data.get("code", "")
        refactor_type = input_data.get("refactor_type", "extract_method")
        
        # Simular refactorización
        refactored_code = code
        
        if refactor_type == "extract_method":
            # Extraer método
            refactored_code = code + "\n\n# Refactored: Method extracted"
        elif refactor_type == "rename":
            # Renombrar
            old_name = input_data.get("old_name", "old")
            new_name = input_data.get("new_name", "new")
            refactored_code = code.replace(old_name, new_name)
        
        return {
            "original_code": code,
            "refactored_code": refactored_code,
            "refactor_type": refactor_type,
            "changes": ["Method extracted" if refactor_type == "extract_method" else "Renamed variables"]
        }
    
    async def _apply_standards(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Aplicar estándares de codificación."""
        code = input_data.get("code", "")
        
        issues = []
        
        # Verificar estándares básicos
        if len(code) > 0:
            # Verificar naming conventions
            if "class" in code:
                if not any(word[0].isupper() for word in code.split() if "class" in code):
                    issues.append("Class names should use PascalCase")
            
            # Verificar docstrings
            if "def " in code and '"""' not in code and "'''" not in code:
                issues.append("Missing docstring")
            
            # Verificar imports al inicio
            lines = code.split("\n")
            import_lines = [i for i, line in enumerate(lines) if line.strip().startswith("import ") or line.strip().startswith("from ")]
            if import_lines and import_lines[0] > 10:
                issues.append("Imports should be at the top of the file")
        
        return {
            "code": code,
            "issues": issues,
            "standards_applied": ["PEP 8", "Type hints", "Docstrings"],
            "issues_count": len(issues)
        }
    
    async def _generate_documentation(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generar documentación de código."""
        modules = input_data.get("modules", [])
        
        docs = []
        
        for module in modules:
            docs.append({
                "module": module.get("name", "unknown"),
                "description": f"Module for {module.get('name', 'unknown')}",
                "classes": [],
                "functions": [],
                "usage": f"from {module.get('file_path', '')} import ..."
            })
        
        return {
            "documentation": docs,
            "format": "sphinx",
            "count": len(docs)
        }
    
    async def _manage_dependencies(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Gestionar dependencias del proyecto."""
        current_deps = input_data.get("dependencies", [])
        new_deps = input_data.get("new_dependencies", [])
        
        all_deps = list(set(current_deps + new_deps))
        
        # Clasificar dependencias
        runtime_deps = [d for d in all_deps if d not in ["pytest", "ruff", "mypy"]]
        dev_deps = [d for d in all_deps if d in ["pytest", "ruff", "mypy"]]
        
        return {
            "all_dependencies": all_deps,
            "runtime_dependencies": runtime_deps,
            "dev_dependencies": dev_deps,
            "conflicts": []
        }
    
    async def shutdown(self) -> None:
        """Limpiar recursos."""
        self.update_state(AgentState.SHUTTING_DOWN)
        logger.info(f"Shutting down {self._name}")
        self.update_state(AgentState.IDLE)
    
    def _generate_model(self, entity_name: str) -> str:
        """Generar modelo SQLAlchemy."""
        template = self._code_templates["sqlalchemy_model"]
        return template.format(
            class_name=entity_name,
            table_name=entity_name.lower() + "s"
        )
    
    def _generate_schema(self, entity_name: str) -> str:
        """Generar esquema Pydantic."""
        template = self._code_templates["fastapi_model"]
        return template.format(class_name=entity_name)
    
    def _generate_service(self, entity_name: str) -> str:
        """Generar servicio."""
        template = self._code_templates["service"]
        return template.format(
            service_name=f"{entity_name}Service",
            model_name=entity_name,
            model_import=f"src.{entity_name.lower()}.model",
            entity=entity_name.lower()
        )
    
    def _generate_route(self, entity_name: str) -> str:
        """Generar ruta FastAPI."""
        template = self._code_templates["fastapi_route"]
        return template.format(
            model_name=entity_name,
            model_import=f"src.{entity_name.lower()}.schema",
            service_import=f"src.{entity_name.lower()}.service",
            service_name=f"{entity_name}Service",
            service_var=entity_name.lower(),
            entity=entity_name.lower()
        )
    
    def _extract_imports(self, code: str) -> List[str]:
        """Extraer imports del código."""
        imports = []
        for line in code.split("\n"):
            if line.strip().startswith("import ") or line.strip().startswith("from "):
                imports.append(line.strip())
        return imports
    
    def get_generated_modules(self) -> Dict[str, CodeModule]:
        """Obtener módulos generados."""
        return self._generated_modules