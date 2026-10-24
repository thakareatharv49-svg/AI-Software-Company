"""Deterministic architecture selection and environment preflight for mission plans.

This module deliberately does not install packages or claim to inspect the host.
The caller supplies a RuntimeCapabilities profile representing the configured
execution environment; unsupported prerequisites are reported before coding.
"""
from __future__ import annotations

import re

from src.company.mission_controller.models import (
    ArchitectureDependency,
    ArchitecturePlan,
    RuntimeCapabilities,
    RequirementsContract,
)
from src.company.models.contracts import CompanyMission


def _has(text: str, *terms: str) -> bool:
    return any(re.search(rf"\\b{re.escape(term)}\\b", text) for term in terms)


def build_architecture_plan(
    mission: CompanyMission,
    contract: RequirementsContract | None = None,
    capabilities: RuntimeCapabilities | None = None,
) -> ArchitecturePlan:
    """Choose a project type/stack from the mission and check it against capabilities."""
    caps = capabilities or RuntimeCapabilities()
    objective = mission.objective.strip().lower()
    evidence: list[str] = []

    if _has(objective, "cli", "command-line", "command line", "terminal utility"):
        project_type = "cli_utility"
        evidence.append("The mission explicitly requests a command-line or terminal utility.")
    elif _has(objective, "api", "rest", "endpoint", "backend service", "http service"):
        project_type = "api_service"
        evidence.append("The mission explicitly requests an API, endpoint, or backend service.")
    elif _has(objective, "library", "sdk", "package"):
        project_type = "python_library"
        evidence.append("The mission explicitly requests a reusable library, SDK, or package.")
    elif _has(objective, "full-stack", "full stack", "frontend and backend", "web app with api"):
        project_type = "full_stack_web_app"
        evidence.append("The mission explicitly requests both a user interface and a service.")
    elif _has(objective, "website", "web app", "web application", "browser", "dashboard", "responsive"):
        project_type = "browser_app"
        evidence.append("The mission emphasizes browser, website, dashboard, or responsive UI behavior.")
    else:
        project_type = "general_python_app"
        evidence.append("No specific delivery type was explicit; selected a conservative Python application baseline.")

    available_languages = {value.lower() for value in caps.languages}
    available_frameworks = {value.lower() for value in caps.frameworks}
    available_tools = {value.lower() for value in caps.tools}
    available_packages = {value.lower() for value in caps.packages}
    available_databases = {value.lower() for value in caps.database_engines}

    language = "python"
    framework: str | None = None
    runtime = "python"
    layout: list[str]
    components: list[str]
    interfaces: list[str]
    data_model: list[str] = []
    validation: list[str]
    dependencies: list[ArchitectureDependency] = []

    if project_type == "browser_app":
        language = "javascript"
        runtime = "browser"
        layout = [
            "index.html",
            "src/styles.css",
            "src/app.js",
            "tests/",
            "README.md",
        ]
        components = ["Application shell", "View/state module", "Accessible UI components", "Persistence adapter"]
        interfaces = ["Browser entry point", "UI event/state contract", "Persistence adapter interface"]
        data_model = ["Define entities and storage schema from the mission's explicit requirements"]
        validation = ["Static HTML/JavaScript checks", "Browser interaction smoke test", "Persistence/reload test", "Responsive layout checks"]
        dependencies.extend([
            ArchitectureDependency(name="html", purpose="Browser document structure", kind="runtime", available="html" in available_languages),
            ArchitectureDependency(name="javascript", purpose="Client behavior", kind="runtime", available="javascript" in available_languages),
            ArchitectureDependency(name="css", purpose="Responsive presentation", kind="runtime", available="css" in available_languages),
        ])
    elif project_type == "api_service":
        framework = "fastapi" if "fastapi" in available_frameworks and "fastapi" in available_packages else None
        language = "python"
        runtime = "python"
        layout = [
            "src/app.py",
            "src/routes/",
            "src/schemas/",
            "src/services/",
            "tests/",
            "pyproject.toml",
            "README.md",
        ]
        components = ["HTTP entry point", "Request/response schemas", "Route handlers", "Business service layer", "Error handling"]
        interfaces = ["HTTP API contract", "Schema/service boundary", "Health/readiness endpoint"]
        data_model = ["Define request/response models", "Select persistence only when required by the mission"]
        validation = ["Import/compile check", "Route contract tests", "Success and error-path tests", "Health endpoint smoke test"]
        if framework:
            dependencies.append(ArchitectureDependency(name="fastapi", purpose="HTTP routing and request validation", available=True))
            dependencies.append(ArchitectureDependency(name="uvicorn", purpose="ASGI development/runtime server", available="uvicorn" in available_packages))
        else:
            evidence.append("FastAPI is unavailable in the supplied capability profile; use a Python standard-library HTTP implementation or flag a required framework.")
    elif project_type == "python_library":
        language = "python"
        runtime = "python"
        layout = ["src/package_name/", "tests/", "pyproject.toml", "README.md"]
        components = ["Public API", "Core implementation modules", "Input validation", "Exceptions"]
        interfaces = ["Documented Python import/API surface", "Stable public function/class signatures"]
        validation = ["Import/compile check", "Public API unit tests", "Packaging/build check"]
    elif project_type == "cli_utility":
        language = "python"
        runtime = "python"
        layout = ["src/cli.py", "src/commands/", "tests/", "pyproject.toml", "README.md"]
        components = ["Argument parser", "Command handlers", "Input/output boundary", "Exit-code mapping"]
        interfaces = ["Documented command-line flags", "Stable exit codes", "Machine-readable output where requested"]
        validation = ["Import/compile check", "Help/usage test", "Command success and failure tests", "Exit-code assertions"]
    elif project_type == "full_stack_web_app":
        language = "python"
        framework = "fastapi" if "fastapi" in available_frameworks and "fastapi" in available_packages else None
        runtime = "python + browser"
        layout = ["src/app.py", "src/routes/", "src/services/", "src/schemas/", "web/index.html", "web/src/app.js", "web/src/styles.css", "tests/", "README.md"]
        components = ["Browser UI", "API route layer", "Business services", "Persistence adapter", "Configuration boundary"]
        interfaces = ["Browser-to-API HTTP contract", "Schema/service boundary", "Persistence adapter interface"]
        data_model = ["Define entities and relationships from explicit requirements"]
        validation = ["Frontend static checks", "API contract tests", "End-to-end UI/API smoke test", "Persistence test"]
        if framework:
            dependencies.append(ArchitectureDependency(name="fastapi", purpose="API routing and request validation", available=True))
    else:
        language = "python"
        runtime = "python"
        layout = ["src/app.py", "src/core/", "tests/", "pyproject.toml", "README.md"]
        components = ["Application entry point", "Core domain logic", "Input/output boundary", "Error handling"]
        interfaces = ["Documented public entry point", "Explicit module boundaries"]
        validation = ["Import/compile check", "Core behavior unit tests", "Input/error-path tests"]

    if language not in available_languages:
        dependencies.append(ArchitectureDependency(
            name=language, purpose="Selected implementation language", kind="runtime",
            available=False, reason="Language is not listed in the configured runtime capabilities.",
        ))
    if "python" in runtime and "python" not in available_tools:
        dependencies.append(ArchitectureDependency(
            name="python", purpose="Execute Python project and validation commands", kind="tool",
            available=False, reason="Python executable is not listed in the configured tool capabilities.",
        ))
    if "pytest" in available_tools:
        dependencies.append(ArchitectureDependency(name="pytest", purpose="Run automated validation", kind="tool", available=True))
    else:
        dependencies.append(ArchitectureDependency(
            name="pytest", purpose="Run automated validation", kind="tool", available=False,
            reason="pytest is not listed in the configured tool capabilities.",
        ))

    if project_type in {"api_service", "full_stack_web_app"} and _has(objective, "persist", "database", "store", "save"):
        if "sqlite" in available_databases:
            dependencies.append(ArchitectureDependency(name="sqlite", purpose="Local relational persistence", kind="database", available=True))
            data_model.append("Use SQLite only for explicitly required persistence; define schema and migration strategy")
        else:
            dependencies.append(ArchitectureDependency(
                name="sqlite", purpose="Local relational persistence", kind="database", available=False,
                reason="SQLite is not listed in the configured database capabilities.",
            ))

    unsupported = sorted({item.name for item in dependencies if item.required and not item.available})
    status = "needs_clarification" if contract is not None and contract.status != "ready" else ("blocked_unsupported_dependency" if unsupported else "ready")
    if unsupported:
        evidence.append("Required runtime capabilities are missing: " + ", ".join(unsupported) + ".")
    return ArchitecturePlan(
        mission_id=mission.id,
        project_type=project_type,
        confidence=0.85 if project_type == "general_python_app" else 0.95,
        rationale=evidence,
        language=language,
        framework=framework,
        runtime=runtime,
        repository_layout=layout,
        components=components,
        interfaces=interfaces,
        data_model=data_model,
        validation_strategy=validation,
        dependencies=dependencies,
        unsupported_dependencies=unsupported,
        status=status,
    )
