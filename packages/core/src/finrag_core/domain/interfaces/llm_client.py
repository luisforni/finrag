from abc import ABC, abstractmethod


class AbstractLLMClient(ABC):
    @abstractmethod
    async def generate(self, question: str, context: str) -> tuple[str, int]: ...
