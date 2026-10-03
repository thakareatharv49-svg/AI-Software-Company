from pydantic import BaseModel, Field


class GitHubRepository(BaseModel):
    owner: str
    name: str
    default_branch: str = "main"


class GitHubIssue(BaseModel):
    title: str
    body: str = ""
    labels: list[str] = Field(default_factory=list)


class GitHubPullRequest(BaseModel):
    title: str
    head: str
    base: str = "main"
    body: str = ""


class GitHubActionResult(BaseModel):
    success: bool
    message: str
    identifier: str | None = None
