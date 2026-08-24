from abc import (
    ABC,
    abstractmethod,
)
from collections.abc import Iterator


class AIProvider(ABC):
    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    def stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> Iterator[str]:
        raise NotImplementedError