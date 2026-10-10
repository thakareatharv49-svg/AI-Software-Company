# AI Software Company

A runnable autonomous software factory with a browser control center.

## Web app

The control center is served by the same FastAPI application:

**http://127.0.0.1:8000/app**

From the web app you can:
- Create and launch missions.
- Watch live company/factory status.
- Inspect mission status and messages.
- View generated project outputs.
- Open the generated GitHub repository.
- Review the mission audit trail.
- Retry failed/blocked missions.
- Cancel missions or stop the company.

The browser UI is intentionally part of the main application, so there is no separate frontend server to configure.

The private owner console is available at **http://127.0.0.1:8000/owner**. Its sign-in page loads before authentication; the company APIs and factory controls remain owner-protected. To sign in, configure `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, and `OWNER_EMAIL` in `.env` (or configure the equivalent GitHub OAuth credentials). Set `PUBLIC_BASE_URL` to the exact local app origin, and register the matching callback URL with the provider, for example `http://127.0.0.1:8000/auth/google/callback`. Without provider credentials, the OAuth start endpoint intentionally returns HTTP 503; without a valid owner session, protected APIs return HTTP 401/403.

## What it does

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

Open http://127.0.0.1:8000/app.

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
