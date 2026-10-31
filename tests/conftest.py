import pytest

from goatllm.config import load_settings

CONFIG_KEYS = (
    "DISCORD_BOT_TOKEN DISCORD_ALLOWED_USER_IDS DISCORD_COMMAND_NAME OLLAMA_BASE_URL "
    "OLLAMA_MODEL OLLAMA_TIMEOUT_SECONDS OLLAMA_KEEP_ALIVE OLLAMA_NUM_CTX OLLAMA_NUM_PREDICT "
    "OLLAMA_THINK MAX_PROMPT_CHARS MAX_CONCURRENT_GENERATIONS LLM_SYSTEM_PROMPT LOG_LEVEL"
).split()


@pytest.fixture
def configured_env(monkeypatch):
    for key in CONFIG_KEYS:
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "test-application-secret")
    monkeypatch.setenv("DISCORD_ALLOWED_USER_IDS", "123,456")
    monkeypatch.setenv("OLLAMA_MODEL", "test-model")
    return monkeypatch


@pytest.fixture
def settings(configured_env):
    return load_settings(None)
