"""Infer a deliverable type from a natural-language software mission."""

from __future__ import annotations


def classify_project_type(name: str, objective: str) -> str:
    """Return a stable target type without requiring a separate user setting."""
    text = f"{name} {objective}".casefold()
    if any(term in text for term in ("react native", "flutter", "android app", "ios app", "mobile app", "mobile application", "apk")):
        return "mobile"
    if any(term in text for term in ("desktop app", "desktop application", "windows app", "macos app", "linux desktop", "electron app", "tauri app")):
        return "desktop"
    if any(term in text for term in ("command-line", "command line", "cli tool", "terminal utility", "shell script")):
        return "cli"
    if any(term in text for term in ("python library", "javascript library", "npm package", "sdk", "reusable package")):
        return "library"
    if any(term in text for term in ("api-only", "api only", "rest api", "backend service", "backend-only", "backend only", "microservice")):
        return "api"
    if any(term in text for term in ("website", "web app", "web application", "browser app", "browser-based", "frontend", "dashboard", "storefront", "landing page")):
        return "web"
    if any(term in text for term in ("game", "video game", "2d game", "3d game")):
        return "game"
    if any(term in text for term in ("automation", "data pipeline", "etl", "scraper", "batch job")):
        return "automation"
    # An unspecified user-facing app defaults to web because the factory preview
    # can run local browser assets without a platform-specific toolchain.
    if any(term in text for term in ("app", "application", "platform", "software product")):
        return "web"
    return "cli"


def project_type_instructions(project_type: str) -> str:
    """Give the generator concrete deliverable guidance for each supported type."""
    instructions = {
        "web": "Deliver a complete web/browser application with a clear entry point, local assets, responsive UI, functional interactions, and browser-appropriate tests.",
        "mobile": "Deliver a real mobile project for the requested platform/framework. Include its package/build configuration, app entry point, navigation, platform-appropriate UI, and tests. Do not substitute a browser-only mockup; if the requested SDK is unavailable, provide complete source and explicit build/run instructions.",
        "desktop": "Deliver a real desktop application for the requested platform/framework, including its project/build configuration, application entry point, native-window integration where appropriate, and tests. Do not substitute a browser-only mockup.",
        "api": "Deliver an API/backend service with application entry point, routes, domain models, input validation, error responses, configuration examples without secrets, and API-level tests. Do not force a browser frontend unless requested.",
        "cli": "Deliver a runnable command-line tool with argument parsing, helpful usage, clear exit codes, error handling, and tests for successful and invalid inputs. Do not force a browser frontend.",
        "library": "Deliver a reusable library/package with public APIs, package metadata, usage examples, type/documentation where appropriate, and behavior-focused tests. Do not force an application UI.",
        "game": "Deliver a playable game matching the requested platform, with a main loop or engine project, meaningful gameplay state, input handling, restart/exit behavior, and tests for core rules where practical.",
        "automation": "Deliver a runnable automation/data-processing project with configurable inputs, safe error handling, repeatable execution, logging that avoids secrets, and tests using local fixtures rather than live services.",
    }
    return instructions.get(project_type, instructions["cli"])
