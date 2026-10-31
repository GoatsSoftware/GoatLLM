import asyncio
import logging
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import discord
import pytest

from goatllm.discord_app import ERROR_MESSAGES, GoatClient
from goatllm.llm.base import GenerationSettings, ProviderError, ProviderErrorCode


def interaction(user_id=123):
    return SimpleNamespace(
        user=SimpleNamespace(id=user_id),
        response=SimpleNamespace(
            defer=AsyncMock(),
            send_message=AsyncMock(),
            is_done=Mock(return_value=False),
        ),
        edit_original_response=AsyncMock(),
    )


def http_error():
    return discord.HTTPException(SimpleNamespace(status=403, reason="Forbidden"), "SENSITIVE")


@pytest.mark.parametrize(("user_id", "prompt"), [(999, "hello"), (123, " "), (123, "a" * 1801)])
async def test_denied_or_invalid_never_generates(settings, user_id, prompt):
    provider = SimpleNamespace(generate=AsyncMock())
    client = GoatClient(settings, provider)
    event = interaction(user_id)
    await client.ask(event, prompt)
    provider.generate.assert_not_called()
    event.response.defer.assert_not_called()
    kwargs = event.response.send_message.call_args.kwargs
    assert kwargs["ephemeral"] is True
    assert kwargs["allowed_mentions"].to_dict() == {"parse": []}
    assert kwargs["suppress_embeds"] is True
    await client.close()


async def test_defer_precedes_provider_and_response_is_public_and_mention_safe(settings):
    event = interaction()

    async def generate(*args):
        event.response.defer.assert_awaited_once_with(thinking=True, ephemeral=False)
        return "@everyone @here <@123> <@&123>"

    provider = SimpleNamespace(generate=AsyncMock(side_effect=generate))
    client = GoatClient(settings, provider)
    await client.ask(event, "only prompt")
    provider.generate.assert_awaited_once_with(
        "only prompt", settings.system_prompt, settings.generation
    )
    kwargs = event.edit_original_response.call_args.kwargs
    assert kwargs["content"] == "@everyone @here <@123> <@&123>"
    assert kwargs["allowed_mentions"].to_dict() == {"parse": []}
    assert client._active == 0
    assert not client._handlers
    await client.close()


@pytest.mark.parametrize("capacity", [1, 2, 4])
async def test_busy_rejects_without_queue_then_capacity_recovers(settings, capacity):
    settings = replace(settings, max_concurrent_generations=capacity)
    entered = asyncio.Event()
    release = asyncio.Event()
    count = 0

    async def generate(*args):
        nonlocal count
        count += 1
        if count == capacity:
            entered.set()
        await release.wait()
        return "ok"

    provider = SimpleNamespace(generate=AsyncMock(side_effect=generate))
    client = GoatClient(settings, provider)
    tasks = [asyncio.create_task(client.ask(interaction(), "hello")) for _ in range(capacity)]
    try:
        await asyncio.wait_for(entered.wait(), 1)
        busy = interaction(456)
        await asyncio.wait_for(client.ask(busy, "second user"), 1)
        assert "busy" in busy.response.send_message.call_args.args[0]
        busy.response.defer.assert_not_called()
        assert provider.generate.await_count == capacity
        release.set()
        await asyncio.gather(*tasks)
        await client.ask(interaction(456), "next")
        assert provider.generate.await_count == capacity + 1
        assert client._active == 0
    finally:
        release.set()
        await client.close()


@pytest.mark.parametrize("code", list(ProviderErrorCode))
async def test_provider_failure_is_safe_and_releases_capacity(settings, code, caplog):
    caplog.set_level(logging.INFO, logger="goatllm")
    provider = SimpleNamespace(generate=AsyncMock(side_effect=ProviderError(code)))
    client = GoatClient(settings, provider)
    event = interaction()
    await client.ask(event, "SENSITIVE_PROMPT")
    assert event.edit_original_response.call_args.kwargs["content"] == ERROR_MESSAGES[code]
    assert "SENSITIVE_PROMPT" not in caplog.text
    assert settings.discord_bot_token not in caplog.text
    assert client._active == 0
    provider.generate.side_effect = None
    provider.generate.return_value = "recovered"
    await client.ask(interaction(), "next")
    assert provider.generate.await_count == 2
    await client.close()


async def test_unexpected_provider_error_never_leaks(settings, caplog):
    caplog.set_level(logging.DEBUG, logger="goatllm")
    provider = SimpleNamespace(generate=AsyncMock(side_effect=RuntimeError("SECRET_ERROR")))
    client = GoatClient(settings, provider)
    event = interaction()
    await client.ask(event, "SECRET_PROMPT")
    assert "SECRET" not in event.edit_original_response.call_args.kwargs["content"]
    assert "SECRET" not in caplog.text
    assert all(record.exc_info is None for record in caplog.records)
    await client.close()


@pytest.mark.parametrize("stage", ["defer", "edit"])
async def test_discord_failure_releases_capacity(settings, stage, caplog):
    provider = SimpleNamespace(generate=AsyncMock(return_value="answer"))
    client = GoatClient(settings, provider)
    event = interaction()
    target = event.response.defer if stage == "defer" else event.edit_original_response
    target.side_effect = http_error()
    await client.ask(event, "SECRET_PROMPT")
    assert client._active == 0
    assert not client._handlers
    assert "SENSITIVE" not in caplog.text
    if stage == "defer":
        provider.generate.assert_not_called()
    await client.close()


async def test_provider_deadline_even_for_noncompliant_adapter(settings):
    settings = replace(settings, generation=GenerationSettings(0.02, 2048, 512))

    async def forever(*args):
        await asyncio.Event().wait()

    client = GoatClient(settings, SimpleNamespace(generate=forever))
    event = interaction()
    await client.ask(event, "prompt")
    assert "too long" in event.edit_original_response.call_args.kwargs["content"]
    assert client._active == 0
    await client.close()


async def test_close_cancels_inflight_provider_and_rejects_new_work(settings):
    entered = asyncio.Event()
    cancelled = asyncio.Event()

    async def forever(*args):
        entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    client = GoatClient(settings, SimpleNamespace(generate=forever))
    task = asyncio.create_task(client.ask(interaction(), "prompt"))
    await asyncio.wait_for(entered.wait(), 1)
    await client.close()
    assert cancelled.is_set()
    assert task.cancelled()
    assert client._active == 0
    assert not client._handlers
    event = interaction()
    await client.ask(event, "prompt")
    event.response.defer.assert_not_called()


async def test_tree_errors_and_failed_rejections_do_not_escape(settings, caplog):
    client = GoatClient(settings, SimpleNamespace(generate=AsyncMock()))
    event = interaction(999)
    event.response.send_message.side_effect = http_error()
    await client.ask(event, "private")
    await client.command_error(event, RuntimeError("SENSITIVE"))
    await client.on_error("SENSITIVE")
    assert "SENSITIVE" not in caplog.text
    await client.close()
