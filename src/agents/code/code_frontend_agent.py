"""Code Frontend Agent for frontend implementation and code generation."""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.agents.base.base_agent import (
    AgentState,
    BaseAgent,
    Capability,
    Task,
    TaskResult,
    TaskStatus,
)

logger = logging.getLogger(__name__)


@dataclass
class FrontendComponent:
    """Componente frontend."""

    id: str
    name: str
    component_type: str  # component, page, hook, service
    framework: str  # react, vue, angular
    props: dict[str, Any] = field(default_factory=dict)
    state: dict[str, Any] = field(default_factory=dict)
    styles: dict[str, Any] = field(default_factory=dict)


@dataclass
class FrontendModule:
    """Módulo frontend generado."""

    id: str
    name: str
    file_path: str
    content: str
    language: str
    framework: str
    imports: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


class CodeFrontendAgent(BaseAgent):
    """Agente especializado en generación de código frontend."""

    def __init__(self) -> None:
        super().__init__(
            agent_id="code_frontend",
            name="Code Frontend Agent",
            description="Agente para implementación de código frontend (React, Vue, Angular)",
        )
        self._generated_modules: dict[str, FrontendModule] = {}
        self._component_templates = self._load_templates()

        self._register_capabilities()

    def _register_capabilities(self) -> None:
        """Registrar las capacidades del agente."""
        self.add_capability(
            Capability(
                name="generate_components",
                description="Generar componentes React/Vue/Angular",
                version="1.0.0",
            )
        )
        self.add_capability(
            Capability(
                name="generate_pages", description="Generar páginas completas", version="1.0.0"
            )
        )
        self.add_capability(
            Capability(name="generate_hooks", description="Generar custom hooks", version="1.0.0")
        )
        self.add_capability(
            Capability(
                name="generate_services", description="Generar servicios API", version="1.0.0"
            )
        )
        self.add_capability(
            Capability(
                name="generate_styles", description="Generar estilos y temas", version="1.0.0"
            )
        )
        self.add_capability(
            Capability(
                name="setup_project", description="Configurar proyecto frontend", version="1.0.0"
            )
        )

    def _load_templates(self) -> dict[str, dict[str, str]]:
        """Cargar plantillas de código frontend."""
        return {
            "react": {
                "component": """import React, {{ useState, useEffect }} from 'react';
import PropTypes from 'prop-types';
import './{component_name}.css';

const {class_name} = ({{ props }}) => {{
  const [state, setState] = useState({initial_state});

  useEffect(() => {{
    // Effect logic here
  }}, []);

  const handleEvent = (event) => {{
    // Event handler logic
  }};

  return (
    <div className="{component_name}">
      {{/* Component JSX */}}
  );
}};

{class_name}.propTypes = {{
  // PropTypes definitions
}};

{class_name}.defaultProps = {{
  // Default props
}};

export default {class_name};
""",
                "page": """import React from 'react';
import {{ useParams, useNavigate }} from 'react-router-dom';
import './{page_name}.css';

const {class_name} = () => {{
  const {{ id }} = useParams();
  const navigate = useNavigate();

  // Page logic here

  return (
    <div className="{page_name}">
      <h1>{page_title}</h1>
      {{/* Page content */}}
    </div>
  );
}};

export default {class_name};
""",
                "hook": """import {{ useState, useEffect, useCallback }} from 'react';

export const use{hook_name} = (params) => {{
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchData = useCallback(async () => {{
    setLoading(true);
    try {{
      // Fetch logic
      const result = await apiCall(params);
      setData(result);
    }} catch (err) {{
      setError(err);
    }} finally {{
      setLoading(false);
    }}
  }}, [params]);

  useEffect(() => {{
    fetchData();
  }}, [fetchData]);

  return {{ data, loading, error, refetch: fetchData }};
}};
""",
                "service": """import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || '/api';

const {service_name} = axios.create({{
  baseURL: API_BASE_URL,
  timeout: 10000,
}});

// Request interceptor
{service_name}.interceptors.request.use(
  (config) => {{
    const token = localStorage.getItem('authToken');
    if (token) {{
      config.headers.Authorization = `Bearer ${{token}}`;
    }}
    return config;
  }},
  (error) => Promise.reject(error)
);

// Response interceptor
{service_name}.interceptors.response.use(
  (response) => response,
  (error) => {{
    if (error.response?.status === 401) {{
      localStorage.removeItem('authToken');
      window.location.href = '/login';
    }}
    return Promise.reject(error);
  }}
);

// API methods
export const get{entity_name} = (id) => {service_name}.get(`/${{entity}}/${{id}}`);
export const list{entity_name} = (params) => {service_name}.get(`/${{entity}}`, {{ params }});
export const create{entity_name} = (data) => {service_name}.post(`/${{entity}}`, data);
export const update{entity_name} = (id, data) => {service_name}.put(`/${{entity}}/${{id}}`, data);
export const delete{entity_name} = (id) => {service_name}.delete(`/${{entity}}/${{id}}`);

export default {service_name};
""",
                "styles": """/* {component_name} styles */
.{class_name} {{
  /* Base styles */
}}

.{class_name}--modifier {{
  /* Modifier styles */
}}

/* Responsive */
@media (max-width: 768px) {{
  .{class_name} {{
    /* Mobile styles */
  }}
}}
""",
            },
            "vue": {
                "component": """<template>
  <div class="{component_name}">
    <!-- Component template -->
  </div>
</template>

<script setup>
import {{ ref, computed, onMounted }} from 'vue';
import './{component_name}.scss';

// Props
const props = defineProps({{
  // Props definition
}});

// Emits
const emit = defineEmits([
// Events
]);

// Reactive state
const state = ref({initial_state});

// Computed
const computedValue = computed(() => {{
  // Computed logic
}});

// Methods
const handleEvent = () => {{
  // Event handler
}};

// Lifecycle
onMounted(() => {{
  // Mount logic
}});
</script>

<style scoped lang="scss">
.{component_name} {{
  // Component styles
}}
</style>
""",
                "page": """<template>
  <div class="{page_name}">
    <h1>{page_title}</h1>
    <!-- Page content -->
  </div>
</template>

<script setup>
import {{ ref, onMounted }} from 'vue';
import {{ useRoute, useRouter }} from 'vue-router';

const route = useRoute();
const router = useRouter();

// Page logic
onMounted(() => {{
  // Mount logic
}});
</script>

<style scoped lang="scss">
.{page_name} {{
  // Page styles
}}
</style>
""",
            },
        }

    async def initialize(self) -> None:
        """Inicializar el agente."""
        self.update_state(AgentState.INITIALIZING)
        logger.info(f"Initializing {self._name}")
        self.update_state(AgentState.IDLE)

    async def execute(self, task: Task) -> TaskResult:
        """Ejecutar una tarea de código frontend."""
        start_time = datetime.now()
        self.update_state(AgentState.PROCESSING)

        try:
            task_type = task.type

            if task_type == "generate_components":
                result = await self._generate_components(task.input_data)
            elif task_type == "generate_pages":
                result = await self._generate_pages(task.input_data)
            elif task_type == "generate_hooks":
                result = await self._generate_hooks(task.input_data)
            elif task_type == "generate_services":
                result = await self._generate_services(task.input_data)
            elif task_type == "generate_styles":
                result = await self._generate_styles(task.input_data)
            elif task_type == "setup_project":
                result = await self._setup_project(task.input_data)
            else:
                raise ValueError(f"Unknown task type: {task_type}")

            execution_time = (datetime.now() - start_time).total_seconds()
            self.update_metrics(execution_time, success=True)
            self.update_state(AgentState.IDLE)

            return TaskResult(
                task_id=task.id,
                status=TaskStatus.COMPLETED,
                output_data=result,
                execution_time=execution_time,
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
                execution_time=execution_time,
            )

    async def _generate_components(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Generar componentes frontend."""
        component_name = input_data.get("component_name", "Component")
        framework = input_data.get("framework", "react")

        template = self._component_templates.get(framework, {}).get("component", "")

        if not template:
            return {"error": f"Framework not supported: {framework}"}

        # Generate component
        content = template.format(
            component_name=component_name, class_name=component_name, initial_state="{}"
        )

        module_obj = FrontendModule(
            id=str(uuid.uuid4()),
            name=component_name,
            file_path=f"src/components/{component_name}/{component_name}.{'jsx' if framework == 'react' else 'vue'}",
            content=content,
            language="javascript",
            framework=framework,
            imports=["react" if framework == "react" else "vue"],
        )

        self._generated_modules[module_obj.id] = module_obj

        # Also generate index export
        index_content = f"export {{ default }} from './{component_name}';"

        return {
            "component_name": component_name,
            "framework": framework,
            "files": {
                "component": {"path": module_obj.file_path, "content": content},
                "index": {
                    "path": f"src/components/{component_name}/index.js",
                    "content": index_content,
                },
                "styles": {
                    "path": f"src/components/{component_name}/{component_name}.{'css' if framework == 'react' else 'scss'}",
                    "content": f"/* {component_name} styles */",
                },
            },
        }

    async def _generate_pages(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Generar páginas completas."""
        page_name = input_data.get("page_name", "Page")
        framework = input_data.get("framework", "react")
        route_path = input_data.get("route_path", f"/{page_name.lower()}")

        template = self._component_templates.get(framework, {}).get("page", "")

        if not template:
            return {"error": f"Framework not supported: {framework}"}

        content = template.format(
            page_name=page_name.lower(),
            page_title=page_name.replace("_", " ").title(),
            class_name=page_name,
        )

        module_obj = FrontendModule(
            id=str(uuid.uuid4()),
            name=page_name,
            file_path=f"src/pages/{page_name}/{page_name}.{'jsx' if framework == 'react' else 'vue'}",
            content=content,
            language="javascript",
            framework=framework,
            imports=["react-router-dom" if framework == "react" else "vue-router"],
        )

        self._generated_modules[module_obj.id] = module_obj

        return {
            "page_name": page_name,
            "framework": framework,
            "route_path": route_path,
            "files": {
                "page": {"path": module_obj.file_path, "content": content},
                "index": {
                    "path": f"src/pages/{page_name}/index.js",
                    "content": f"export {{ default }} from './{page_name}.{'jsx' if framework == 'react' else 'vue'}';",
                },
            },
        }

    async def _generate_hooks(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Generar custom hooks."""
        hook_name = input_data.get("hook_name", "useCustom")
        framework = input_data.get("framework", "react")

        template = self._component_templates.get(framework, {}).get("hook", "")

        if not template:
            return {"error": f"Framework not supported: {framework}"}

        content = template.format(hook_name=hook_name)

        module_obj = FrontendModule(
            id=str(uuid.uuid4()),
            name=hook_name,
            file_path=f"src/hooks/{hook_name}.js",
            content=content,
            language="javascript",
            framework=framework,
            imports=["react"],
        )

        self._generated_modules[module_obj.id] = module_obj

        return {
            "hook_name": hook_name,
            "framework": framework,
            "file": {"path": module_obj.file_path, "content": content},
        }

    async def _generate_services(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Generar servicios API."""
        service_name = input_data.get("service_name", "api")
        entity = input_data.get("entity", "entity")
        framework = input_data.get("framework", "react")

        template = self._component_templates.get(framework, {}).get("service", "")

        if not template:
            return {"error": f"Framework not supported: {framework}"}

        content = template.format(
            service_name=service_name, entity_name=entity.title(), entity=entity.lower()
        )

        module_obj = FrontendModule(
            id=str(uuid.uuid4()),
            name=service_name,
            file_path=f"src/services/{service_name}.js",
            content=content,
            language="javascript",
            framework=framework,
            imports=["axios"],
        )

        self._generated_modules[module_obj.id] = module_obj

        return {
            "service_name": service_name,
            "entity": entity,
            "framework": framework,
            "file": {"path": module_obj.file_path, "content": content},
        }

    async def _generate_styles(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Generar estilos y temas."""
        component_name = input_data.get("component_name", "Component")
        framework = input_data.get("framework", "react")
        style_type = input_data.get("style_type", "css")  # css, scss, styled

        template = self._component_templates.get(framework, {}).get("styles", "")

        if not template:
            template = "/* {component_name} styles */\n.{class_name} {{ }}\n"

        content = template.format(component_name=component_name, class_name=component_name)

        return {"component_name": component_name, "style_type": style_type, "content": content}

    async def _setup_project(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Configurar proyecto frontend."""
        project_name = input_data.get("project_name", "frontend")
        framework = input_data.get("framework", "react")
        typescript = input_data.get("typescript", False)

        files = {}

        if framework == "react":
            # package.json
            files["package.json"] = self._generate_react_package_json(project_name, typescript)

            # vite.config.js
            files["vite.config.js"] = self._generate_vite_config()

            # index.html
            files["index.html"] = self._generate_index_html(project_name)

            # src/main.jsx
            files["src/main.jsx"] = self._generate_main_jsx(typescript)

            # src/App.jsx
            files["src/App.jsx"] = self._generate_app_jsx(typescript)

            # src/index.css
            files["src/index.css"] = self._generate_global_css()

        return {
            "project_name": project_name,
            "framework": framework,
            "typescript": typescript,
            "files": files,
        }

    async def shutdown(self) -> None:
        """Limpiar recursos."""
        self.update_state(AgentState.SHUTTING_DOWN)
        logger.info(f"Shutting down {self._name}")
        self.update_state(AgentState.IDLE)

    def _generate_react_package_json(self, project_name: str, typescript: bool) -> str:
        """Generar package.json para React."""
        deps = {"react": "^18.2.0", "react-dom": "^18.2.0", "react-router-dom": "^6.20.0"}
        dev_deps = {"@vitejs/plugin-react": "^4.2.0", "vite": "^5.0.0"}

        if typescript:
            deps["typescript"] = "^5.3.0"

        return f'''{{
  "name": "{project_name}",
  "version": "1.0.0",
  "type": "module",
  "scripts": {{
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  }},
  "dependencies": {{ {", ".join([f'"{k}": "{v}"' for k, v in deps.items()])} }},
  "devDependencies": {{ {", ".join([f'"{k}": "{v}"' for k, v in dev_deps.items()])} }}
}}'''

    def _generate_vite_config(self) -> str:
        """Generar configuración de Vite."""
        return """import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
"""

    def _generate_index_html(self, project_name: str) -> str:
        """Generar index.html."""
        return f"""<!DOCTYPE html>
<html lang="es">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{project_name}</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
"""

    def _generate_main_jsx(self, typescript: bool) -> str:
        ext = "tsx" if typescript else "jsx"
        return f"""import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.{ext}';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
"""

    def _generate_app_jsx(self, typescript: bool) -> str:
        ext = "tsx" if typescript else "jsx"
        return """import React from 'react';
import {{ BrowserRouter, Routes, Route }} from 'react-router-dom';

function App() {{
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<> <div>Home</div> </>} />
      </Routes>
    </BrowserRouter>
  );
}}

export default App;
""".replace("{ext}", ext)

    def _generate_global_css(self) -> str:
        """Generar CSS global."""
        return """* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

#root {
  min-height: 100vh;
}
"""

    def get_generated_modules(self) -> dict[str, FrontendModule]:
        """Obtener módulos generados."""
        return self._generated_modules
