"""Small provider contract independent of Discord and HTTP transport."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


@dataclass(frozen=True, slots=True)
class GenerationSettings:
    """Portable limits passed to a provider for one stateless generation."""

    timeout_seconds: float
    num_ctx: int
    num_predict: int


class ProviderErrorCode(StrEnum):
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"
    MODEL_NOT_FOUND = "model_not_found"
    INVALID_RESPONSE = "invalid_response"
    GENERATION_FAILED = "generation_failed"


class ProviderError(Exception):
    """Safe classification without backend response bodies or request content."""

    def __init__(self, code: ProviderErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


class LLMProvider(Protocol):
    async def generate(
        self,
        prompt: str,
        system_prompt: str,
        generation_settings: GenerationSettings,
    ) -> str:
        """Return final answer text or raise ProviderError; never persist content."""
        ...
