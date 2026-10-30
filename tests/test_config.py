from dataclasses import FrozenInstanceError

import pytest

from goatllm.config import ConfigError, load_settings


def test_defaults_private_bounded_redacted(settings):
    assert settings.allowed_user_ids == {123, 456}
    assert settings.generation.timeout_seconds == 120
    assert settings.ollama_keep_alive == 0
    assert settings.ollama_think is False
    assert settings.max_concurrent_generations == 1
    assert settings.discord_bot_token not in repr(settings)
    assert "123" not in repr(settings)
    with pytest.raises(FrozenInstanceError):
        settings.command_name = "other"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("DISCORD_BOT_TOKEN", ""),
        ("DISCORD_BOT_TOKEN", "replace_me"),
        ("DISCORD_BOT_TOKEN", "secret token"),
        ("DISCORD_ALLOWED_USER_IDS", ""),
        ("DISCORD_ALLOWED_USER_IDS", "123,"),
        ("DISCORD_ALLOWED_USER_IDS", "a-user"),
        ("DISCORD_ALLOWED_USER_IDS", "0"),
        ("DISCORD_ALLOWED_USER_IDS", str(2**64)),
        ("DISCORD_ALLOWED_USER_IDS", "١٢٣"),
        ("DISCORD_COMMAND_NAME", "Ask"),
        ("DISCORD_COMMAND_NAME", "a" * 33),
        ("OLLAMA_MODEL", ""),
        ("OLLAMA_MODEL", "bad\nmodel"),
        ("OLLAMA_TIMEOUT_SECONDS", "nan"),
        ("OLLAMA_TIMEOUT_SECONDS", "inf"),
        ("OLLAMA_TIMEOUT_SECONDS", "0"),
        ("OLLAMA_TIMEOUT_SECONDS", "601"),
        ("OLLAMA_TIMEOUT_SECONDS", "secret"),
        ("OLLAMA_KEEP_ALIVE", "-1"),
        ("OLLAMA_KEEP_ALIVE", "31m"),
        ("OLLAMA_KEEP_ALIVE", "0s"),
        ("OLLAMA_NUM_CTX", "511"),
        ("OLLAMA_NUM_CTX", "32769"),
        ("OLLAMA_NUM_PREDICT", "-1"),
        ("OLLAMA_NUM_PREDICT", "2049"),
        ("OLLAMA_THINK", "maybe"),
        ("MAX_PROMPT_CHARS", "6001"),
        ("MAX_CONCURRENT_GENERATIONS", "0"),
        ("MAX_CONCURRENT_GENERATIONS", "5"),
        ("LLM_SYSTEM_PROMPT", ""),
        ("LLM_SYSTEM_PROMPT", "s" * 4001),
        ("LOG_LEVEL", "TRACE"),
    ],
)
def test_invalid_fields(configured_env, field, value):
    configured_env.setenv(field, value)
    with pytest.raises(ConfigError, match=field) as caught:
        load_settings(None)
    assert "test-application-secret" not in str(caught.value)


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com",
        "https://localhost",
        "http://localhost.evil",
        "http://0.0.0.0",
        "http://user:secret@localhost",
        "http://localhost/api",
        "http://localhost?secret=x",
        "http://localhost#secret",
        "http://localhost:0",
        "http://localhost:65536",
        "http://localhost:",
        "http://[::1",
        "http://local\nhost",
        "file:///tmp/test",
    ],
)
def test_only_loopback_roots(configured_env, url):
    configured_env.setenv("OLLAMA_BASE_URL", url)
    with pytest.raises(ConfigError, match="OLLAMA_BASE_URL"):
        load_settings(None)


@pytest.mark.parametrize(
    "url", ["http://localhost:11434/", "http://[::1]:11434", "http://127.0.0.1"]
)
def test_valid_urls(configured_env, url):
    configured_env.setenv("OLLAMA_BASE_URL", url)
    assert load_settings(None).ollama_base_url == url.rstrip("/")


def test_file_precedence_and_literal_expansion(configured_env, tmp_path):
    path = tmp_path / ".env"
    path.write_text(
        'DISCORD_BOT_TOKEN=other-secret\nLLM_SYSTEM_PROMPT="literal ${DISCORD_BOT_TOKEN}"\n'
        "OLLAMA_KEEP_ALIVE=30m\nOLLAMA_THINK=auto\nDISCORD_ALLOWED_USER_IDS=789\n",
        encoding="utf-8",
    )
    settings = load_settings(path)
    assert settings.discord_bot_token == "test-application-secret"
    assert settings.allowed_user_ids == {123, 456}
    assert settings.system_prompt == "literal ${DISCORD_BOT_TOKEN}"
    assert settings.ollama_keep_alive == "30m"
    assert settings.ollama_think is None


def test_deduplicated_ids(configured_env):
    configured_env.setenv("DISCORD_ALLOWED_USER_IDS", " 123,123, 456 ")
    assert load_settings(None).allowed_user_ids == {123, 456}
