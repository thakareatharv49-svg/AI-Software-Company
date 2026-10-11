# AI Software Developer

The AI Software Developer venture runs an autonomous software factory with a browser control center. The GitHub repository name remains `AI-Software-Company` to preserve existing links and integrations.

## Company structure

Nexora HQ is the parent-company dashboard for tracking ventures, company-level activity, and integration health. AI Software Developer owns software mission execution, generated applications, previews, and its internal factory workflows. Nexora HQ does not replace the factory and its read-only live-status adapter is a separate integration task.

## Web app

The control center is served by the same FastAPI application:

**http://127.0.0.1:8000/app**

From the AI Software Developer control center you can:
- Create and launch missions.
- Watch live company/factory status.
- Inspect mission status and messages.
- View generated project outputs.
- Open the generated GitHub repository.
- Review the mission audit trail.
- Retry failed/blocked missions.
- Cancel missions or stop the company.

The browser UI is intentionally part of the main application, so there is no separate frontend server to configure.

### Local access without a separate owner login

For a single-user development instance, set `LOCAL_ACCESS_ENABLED=true` in your local `.env`. The bypass only applies when `ENVIRONMENT=development` and the request comes from a loopback address (127.0.0.1 or ::1). This lets you use the local factory dashboard without configuring Google/GitHub OAuth or a separate company-owner account. Keep this setting false for shared, hosted, or production environments. Production/shared access continues to require the authenticated session and owner membership.

The legacy owner console remains at **http://127.0.0.1:8000/owner** for deployments that use the sign-in flow.

## What AI Software Developer does

1. You give the company a software mission from the web control center.
2. The local Ollama model turns the mission into a small runnable project.
3. The company materializes the project in an isolated workspace.
4. Automated tests run inside the workspace.
5. QA and security gates run before completion.
6. Generated project files are published directly to the target repository's default branch.
7. The result is recorded in the company dashboard.

## Run locally

Requirements: Python 3.13+, PostgreSQL 16+, and Ollama with the configured model.

PowerShell:

    cd C:\Users\TestUser123\Documents\Projects\AI-Software-Company
    .venv\Scripts\Activate.ps1
    pip install -e ".[dev]"

Create `.env` from `.env.example`, start PostgreSQL, then:

    alembic upgrade head
    uvicorn src.main:app --reload

Open http://127.0.0.1:8000/app. To avoid the separate owner sign-in for your local instance, add `LOCAL_ACCESS_ENABLED=true` to `.env` and restart the server.

The default model is `llama3.2`. Start Ollama and make sure the model is available:

    ollama serve
    ollama pull llama3.2

GitHub delivery can be enabled with a GitHub token:

    GITHUB_TOKEN=your_token
    GITHUB_ALLOW_WRITES=true
    GITHUB_REPOSITORY_OWNER=thakareatharv49-svg
    GITHUB_DEFAULT_BRANCH=main
    GITHUB_BRANCH_PREFIX=factory

Each successful mission gets its own GitHub repository and the generated project is committed directly to its default branch. No pull request is required.

GitHub and deployment integrations remain optional and are protected by the existing gates.
