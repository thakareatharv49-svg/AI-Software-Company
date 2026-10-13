# AI Software Developer

The AI Software Developer venture runs an autonomous software factory with a browser control center. The GitHub repository name remains `AI-Software-Company` to preserve existing links and integrations.

## Company structure

Nexora HQ is the parent-company dashboard for tracking ventures, company-level activity, and integration health. AI Software Developer owns software mission execution, generated applications, previews, and its internal factory workflows. The optional `/api/hq/status` endpoint exposes aggregate mission counts to Nexora HQ using a dedicated bearer token; it does not expose mission details or any execution controls.

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

### Nexora HQ read-only status integration

To allow HQ to read aggregate factory status, set `NEXORA_HQ_STATUS_TOKEN` in the AI Software Developer server's `.env` to a randomly generated secret of at least 32 characters, then restart the server. The dedicated `GET /api/hq/status` endpoint requires `Authorization: Bearer <token>` and returns only explicit service status, active/queued/completed/blocked counts, and a UTC snapshot timestamp. It never exposes mission names, objectives, repository contents, credentials, or mutation endpoints.

Configure Nexora HQ separately with `NEXORA_AI_SOFTWARE_DEVELOPER_URL` set to the AI Software Developer base URL and `NEXORA_AI_SOFTWARE_DEVELOPER_TOKEN` set to the same secret. Keep both values server-side. Use HTTPS outside local development; never put this token in browser code or commit a real token to Git.

### Local access without a separate owner login

For a single-user development instance, set `LOCAL_ACCESS_ENABLED=true` in your local `.env`. The bypass only applies when `ENVIRONMENT=development` and the request comes from a loopback address (127.0.0.1 or ::1). This lets you use the local factory dashboard without configuring Google/GitHub OAuth or a separate company-owner account. Keep this setting false for shared, hosted, or production environments. Production/shared access continues to require the authenticated session and owner membership.

The legacy owner console remains at **http://127.0.0.1:8000/owner** for deployments that use the sign-in flow.

## What AI Software Developer does

1. You give the company a software mission from the web control center.
2. The local Ollama model turns the mission into a small runnable project.
3. The company materializes the project in an isolated workspace and executes generated code in a restricted Docker container by default.
4. Automated tests run inside the workspace.
5. QA and security gates run before completion.
6. The exact reviewed artifact is held behind approval and publication gates; publishing is blocked if its digest changes or required checks fail.
7. The result is recorded in the company dashboard.

## Run locally

Requirements: Python 3.13+, PostgreSQL 16+, Ollama with the configured model, and Docker Desktop (or Docker Engine) for isolated generated-code execution.

PowerShell:

    cd C:\Users\TestUser123\Documents\Projects\AI-Software-Company
    .venv\Scripts\Activate.ps1
    pip install -e ".[dev]"

Create `.env` from `.env.example`, build the restricted execution image, start PostgreSQL, then:

    docker build -t ai-software-company-sandbox:latest docker/sandbox
    alembic upgrade head

For an existing installation, `.env` overrides the new defaults: set `SANDBOX_MODE=container` in your current `.env`, build the image above, and restart the server. `SANDBOX_MODE=host` is an explicit local-development exception and does not provide OS-level isolation.
    uvicorn src.main:app --reload

Open http://127.0.0.1:8000/app. To avoid the separate owner sign-in for your local instance, add `LOCAL_ACCESS_ENABLED=true` to `.env` and restart the server.

The default model is `llama3.2`. Start Ollama and make sure the model is available:

Project generation is bounded by `FACTORY_MAX_GENERATED_PROJECT_FILES` (default `40`, allowed range `4`–`200`). Raise it gradually for larger products after checking model quality, RAM, and runtime; a larger file budget increases capacity but does not guarantee that a model can correctly implement every file.

    ollama serve
    ollama pull llama3.2

GitHub delivery can be enabled with a GitHub token:

    GITHUB_TOKEN=your_token
    GITHUB_ALLOW_WRITES=true
    GITHUB_REPOSITORY_OWNER=thakareatharv49-svg
    GITHUB_DEFAULT_BRANCH=main
    GITHUB_BRANCH_PREFIX=factory

GitHub publishing is gated by the review workflow: required tests and security checks must pass, and the user must approve the exact artifact before publication. If the artifact changes after approval, publishing is rejected. Configure GitHub writes only when you are ready to enable this integration.

GitHub and deployment integrations remain optional and are protected by the existing gates.
