from pydantic import BaseModel


class ModelRequest(BaseModel):
    prompt: str
    model: str | None = None
    system: str | None = None
    temperature: float = 0.2


class ModelResponse(BaseModel):
    content: str
    model: str
    provider: str
    duration_ms: int | None = None
