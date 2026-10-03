from abc import ABC, abstractmethod

from runtime.models.messages import ModelRequest, ModelResponse


class ModelProvider(ABC):
    name: str

    @abstractmethod
    async def generate(self, request: ModelRequest) -> ModelResponse:
        raise NotImplementedError

    @abstractmethod
    async def health(self) -> bool:
        raise NotImplementedError
