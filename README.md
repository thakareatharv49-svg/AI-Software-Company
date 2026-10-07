# AI Software Company

A runnable autonomous software factory.

## What it does
1. You give the company a software mission from the web control center.
2. The local Ollama model turns the mission into a small runnable project.
3. The company materializes the project in an isolated workspace.
4. Automated tests run inside the workspace.
5. QA and security gates run before completion.
6. The result is recorded in the company dashboard.

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

GitHub delivery can be enabled with a GitHub token and target repository:

    GITHUB_TOKEN=your_token
    GITHUB_ALLOW_WRITES=true
    GITHUB_REPOSITORY_OWNER=thakareatharv49-svg
# GITHUB_REPOSITORY_NAME is not required; each mission gets its own repository.
        GITHUB_DEFAULT_BRANCH=main
    GITHUB_BRANCH_PREFIX=factory

With these settings, a successful factory run creates a branch, publishes the generated project files, opens a pull request, and records the repository/PR result in the mission output.

GitHub and deployment integrations remain optional and are protected by the existing gates.