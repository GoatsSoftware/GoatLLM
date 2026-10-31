"""Bounded, stateless non-streaming Ollama chat requests."""

import asyncio
import json

import httpx

from goatllm.llm.base import GenerationSettings, ProviderError, ProviderErrorCode

MAX_RESPONSE_BYTES = 1024 * 1024


class OllamaProvider:
    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        model: str,
        keep_alive: int | str = 0,
        think: bool | None = False,
    ) -> None:
        self._client = client
        self._model = model
        self._keep_alive = keep_alive
        self._think = think

    async def generate(
        self,
        prompt: str,
        system_prompt: str,
        generation_settings: GenerationSettings,
    ) -> str:
        payload = {
            "model": self._model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "keep_alive": self._keep_alive,
            "options": {
                "num_ctx": generation_settings.num_ctx,
                "num_predict": generation_settings.num_predict,
            },
        }
        if self._think is not None:
            payload["think"] = self._think
        try:
            async with asyncio.timeout(generation_settings.timeout_seconds):
                async with self._client.stream(
                    "POST",
                    "/api/chat",
                    json=payload,
                    timeout=httpx.Timeout(generation_settings.timeout_seconds),
                ) as response:
                    if response.status_code == 404:
                        raise ProviderError(ProviderErrorCode.MODEL_NOT_FOUND)
                    if not 200 <= response.status_code < 300:
                        raise ProviderError(ProviderErrorCode.GENERATION_FAILED)
                    body = bytearray()
                    # Decode transport chunks incrementally, but request a single JSON
                    # answer from Ollama. Bound both the read time and decoded size.
                    async for chunk in response.aiter_bytes(chunk_size=65536):
                        if len(body) + len(chunk) > MAX_RESPONSE_BYTES:
                            raise ProviderError(ProviderErrorCode.INVALID_RESPONSE)
                        body.extend(chunk)
                    data = json.loads(body)
                    if not isinstance(data, dict):
                        raise ProviderError(ProviderErrorCode.INVALID_RESPONSE)
                    if "error" in data:
                        raise ProviderError(ProviderErrorCode.GENERATION_FAILED)
                    message = data.get("message")
                    content = message.get("content") if isinstance(message, dict) else None
                    if (
                        data.get("done") is not True
                        or not isinstance(content, str)
                        or not content.strip()
                    ):
                        raise ProviderError(ProviderErrorCode.INVALID_RESPONSE)
                    return content
        except (TimeoutError, httpx.TimeoutException):
            raise ProviderError(ProviderErrorCode.TIMEOUT) from None
        except httpx.RequestError:
            raise ProviderError(ProviderErrorCode.UNAVAILABLE) from None
        except (ValueError, UnicodeError, RecursionError):
            raise ProviderError(ProviderErrorCode.INVALID_RESPONSE) from None
