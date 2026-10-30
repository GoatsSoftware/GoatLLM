import asyncio
import json

import httpx
import pytest

from goatllm.llm.base import GenerationSettings, ProviderError, ProviderErrorCode
from goatllm.llm.ollama import MAX_RESPONSE_BYTES, OllamaProvider

LIMITS = GenerationSettings(1, 2048, 512)


async def test_payload_is_stateless_and_only_final_content_returned():
    requests = []

    def handle(request):
        assert request.url == "http://127.0.0.1:11434/api/chat"
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "done": True,
                "message": {"content": "answer", "thinking": "private reasoning"},
            },
        )

    async with httpx.AsyncClient(
        base_url="http://127.0.0.1:11434",
        transport=httpx.MockTransport(handle),
    ) as client:
        provider = OllamaProvider(client, model="chosen", keep_alive="2m", think=False)
        assert await provider.generate("first", "system", LIMITS) == "answer"
        assert await provider.generate("second", "system", LIMITS) == "answer"
    assert requests == [
        {
            "model": "chosen",
            "stream": False,
            "keep_alive": "2m",
            "think": False,
            "options": {"num_ctx": 2048, "num_predict": 512},
            "messages": [
                {"role": "system", "content": "system"},
                {"role": "user", "content": prompt},
            ],
        }
        for prompt in ("first", "second")
    ]


async def test_auto_thinking_omits_field():
    def handle(request):
        payload = json.loads(request.content)
        assert "think" not in payload
        assert payload["keep_alive"] == 0
        return httpx.Response(200, json={"done": True, "message": {"content": "ok"}})

    async with httpx.AsyncClient(
        base_url="http://localhost",
        transport=httpx.MockTransport(handle),
    ) as client:
        await OllamaProvider(client, model="chosen", think=None).generate("p", "s", LIMITS)


@pytest.mark.parametrize(
    ("status", "data", "code"),
    [
        (404, {}, ProviderErrorCode.MODEL_NOT_FOUND),
        (500, {"error": "SENSITIVE backend details"}, ProviderErrorCode.GENERATION_FAILED),
        (302, {}, ProviderErrorCode.GENERATION_FAILED),
        (200, {"error": "SENSITIVE"}, ProviderErrorCode.GENERATION_FAILED),
        (200, [], ProviderErrorCode.INVALID_RESPONSE),
        (200, {}, ProviderErrorCode.INVALID_RESPONSE),
        (
            200,
            {"done": False, "message": {"content": "partial"}},
            ProviderErrorCode.INVALID_RESPONSE,
        ),
        (200, {"done": True, "message": {"content": "  "}}, ProviderErrorCode.INVALID_RESPONSE),
        (200, {"done": True, "message": {"content": None}}, ProviderErrorCode.INVALID_RESPONSE),
        (200, {"done": True, "message": {"content": 12}}, ProviderErrorCode.INVALID_RESPONSE),
        (200, {"done": True, "message": []}, ProviderErrorCode.INVALID_RESPONSE),
    ],
)
async def test_classified_failures_hide_raw_details(status, data, code):
    async with httpx.AsyncClient(
        base_url="http://localhost",
        transport=httpx.MockTransport(lambda r: httpx.Response(status, json=data)),
    ) as client:
        with pytest.raises(ProviderError) as caught:
            await OllamaProvider(client, model="chosen").generate("SENSITIVE", "SENSITIVE", LIMITS)
    assert caught.value.code is code
    assert "SENSITIVE" not in str(caught.value)


@pytest.mark.parametrize("body", [b"not json", b"\xff", b"x" * (MAX_RESPONSE_BYTES + 1)])
async def test_invalid_or_oversized_body(body):
    async with httpx.AsyncClient(
        base_url="http://localhost",
        transport=httpx.MockTransport(lambda r: httpx.Response(200, content=body)),
    ) as client:
        with pytest.raises(ProviderError) as caught:
            await OllamaProvider(client, model="chosen").generate("p", "s", LIMITS)
    assert caught.value.code is ProviderErrorCode.INVALID_RESPONSE


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (httpx.ConnectError("private-url"), ProviderErrorCode.UNAVAILABLE),
        (httpx.ReadTimeout("private-url"), ProviderErrorCode.TIMEOUT),
    ],
)
async def test_network_failures(error, code):
    def handle(request):
        raise error

    async with httpx.AsyncClient(
        base_url="http://localhost",
        transport=httpx.MockTransport(handle),
    ) as client:
        with pytest.raises(ProviderError) as caught:
            await OllamaProvider(client, model="chosen").generate("p", "s", LIMITS)
    assert caught.value.code is code
    assert "private-url" not in str(caught.value)


async def test_absolute_deadline_closes_slow_response():
    closed = asyncio.Event()

    class SlowStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            while True:
                yield b" "
                await asyncio.sleep(0.01)

        async def aclose(self):
            closed.set()

    async with httpx.AsyncClient(
        base_url="http://localhost",
        transport=httpx.MockTransport(lambda r: httpx.Response(200, stream=SlowStream())),
    ) as client:
        with pytest.raises(ProviderError) as caught:
            await OllamaProvider(client, model="chosen").generate(
                "p",
                "s",
                GenerationSettings(0.04, 2048, 512),
            )
    assert caught.value.code is ProviderErrorCode.TIMEOUT
    assert closed.is_set()


async def test_cancellation_propagates():
    entered = asyncio.Event()

    async def handle(request):
        entered.set()
        await asyncio.Event().wait()

    async with httpx.AsyncClient(
        base_url="http://localhost",
        transport=httpx.MockTransport(handle),
    ) as client:
        task = asyncio.create_task(
            OllamaProvider(client, model="chosen").generate("p", "s", LIMITS)
        )
        await asyncio.wait_for(entered.wait(), 1)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
