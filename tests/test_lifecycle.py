import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from goatllm import __main__ as cli
from goatllm.discord_app import GoatClient


async def test_sync_only_in_setup_not_on_reconnect(settings):
    client = GoatClient(settings, SimpleNamespace(generate=AsyncMock()))
    client.tree.sync = AsyncMock()
    await client.setup_hook()
    await client.on_ready()
    await client.on_ready()
    client.tree.sync.assert_awaited_once()
    await client.close()


@pytest.mark.parametrize("failure", [None, RuntimeError("PRIVATE startup")])
async def test_run_closes_discord_before_http_and_never_preloads(settings, monkeypatch, failure):
    events = []

    class FakeHTTP:
        def __init__(self, **kwargs):
            assert kwargs["trust_env"] is False
            assert kwargs["follow_redirects"] is False

        async def __aenter__(self):
            events.append("http_open")
            return self

        async def __aexit__(self, *args):
            events.append("http_close")

    class FakeDiscord:
        def __init__(self, actual_settings, provider):
            assert actual_settings is settings

        async def __aenter__(self):
            events.append("discord_open")
            return self

        async def start(self, token):
            assert token == settings.discord_bot_token
            events.append("discord_start")
            if failure:
                raise failure

        async def __aexit__(self, *args):
            events.append("discord_close")

    monkeypatch.setattr(cli.httpx, "AsyncClient", FakeHTTP)
    monkeypatch.setattr(cli, "GoatClient", FakeDiscord)
    if failure:
        with pytest.raises(RuntimeError):
            await cli.run(settings)
    else:
        await cli.run(settings)
    assert events == ["http_open", "discord_open", "discord_start", "discord_close", "http_close"]


@pytest.mark.parametrize(
    ("failure", "expected"), [(KeyboardInterrupt(), 0), (RuntimeError("SECRET"), 1)]
)
def test_cli_handles_interrupt_and_startup_error_safely(
    settings, monkeypatch, capsys, failure, expected
):
    monkeypatch.setattr(cli, "load_settings", lambda: settings)

    async def fail(settings):
        raise failure

    monkeypatch.setattr(cli, "run", fail)
    try:
        assert cli.main([]) == expected
        output = capsys.readouterr()
        assert "SECRET" not in output.err
        assert "Traceback" not in output.err
    finally:
        logging.getLogger("goatllm").handlers.clear()
        logging.getLogger("goatllm").propagate = True


def test_debug_dependency_logs_cannot_expose_payloads(capsys):
    cli.configure_logging(logging.DEBUG)
    try:
        logging.getLogger("httpx").error("PRIVATE_HTTP")
        logging.getLogger("discord.gateway").critical("PRIVATE_DISCORD")
        logging.getLogger("goatllm").info("safe_event")
        output = capsys.readouterr().err
        assert "safe_event" in output
        assert "PRIVATE" not in output
    finally:
        logging.getLogger("goatllm").handlers.clear()
        logging.getLogger("goatllm").propagate = True
