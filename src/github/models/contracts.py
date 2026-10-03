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


class GitHubBranch(BaseModel):
    name: str
    sha: str


class GitHubFile(BaseModel):
    path: str
    content: str
    sha: str | None = None


class GitHubCheckRun(BaseModel):
    name: str
    status: str
    conclusion: str | None = None


class GitHubActionResult(BaseModel):
    success: bool
    message: str
    identifier: str | None = None
