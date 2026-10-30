"""Explicit, fail-closed settings; importing this module does not read .env."""

import logging
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv

from goatllm.llm.base import GenerationSettings

DEFAULT_SYSTEM_PROMPT = "You are a helpful, concise assistant in a Discord friends chat."


class ConfigError(ValueError):
    """A safe field/rule message without supplied configuration values."""


@dataclass(frozen=True, slots=True, repr=False)
class Settings:
    discord_bot_token: str
    allowed_user_ids: frozenset[int]
    command_name: str
    ollama_base_url: str
    ollama_model: str
    ollama_keep_alive: int | str
    ollama_think: bool | None
    generation: GenerationSettings
    max_prompt_chars: int
    max_concurrent_generations: int
    system_prompt: str
    log_level: int


def _text(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _integer(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = _text(name, str(default))
    if not re.fullmatch(r"[0-9]{1,10}", raw):
        raise ConfigError(f"{name} must be an integer within its documented bounds.")
    value = int(raw)
    if not minimum <= value <= maximum:
        raise ConfigError(f"{name} is outside its documented bounds.")
    return value


def _base_url() -> str:
    raw = _text("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    try:
        url = urlsplit(raw)
        valid = (
            not any(char.isspace() or ord(char) < 32 for char in raw)
            and url.scheme == "http"
            and url.hostname in {"localhost", "127.0.0.1", "::1"}
            and url.username is None
            and url.password is None
            and url.path in {"", "/"}
            and not url.query
            and not url.fragment
            and (url.port is None or 1 <= url.port <= 65535)
            and not url.netloc.endswith(":")
            and "?" not in raw
            and "#" not in raw
        )
    except ValueError:
        valid = False
    if not valid:
        raise ConfigError("OLLAMA_BASE_URL must be an HTTP loopback root URL with a valid port.")
    return raw.rstrip("/")


def load_settings(env_file: Path | None = Path(".env")) -> Settings:
    """Load only the specified file; the existing environment takes precedence."""
    if env_file is not None:
        logger = logging.getLogger("dotenv.main")
        previous_disabled = logger.disabled
        logger.disabled = True  # Parser warnings can contain source text.
        try:
            load_dotenv(env_file, override=False, interpolate=False, encoding="utf-8")
        except (OSError, UnicodeError):
            raise ConfigError("Unable to read the local environment file.") from None
        finally:
            logger.disabled = previous_disabled

    token = _text("DISCORD_BOT_TOKEN")
    if not token or token == "replace_me" or any(c.isspace() or ord(c) < 32 for c in token):
        raise ConfigError("DISCORD_BOT_TOKEN must contain an application bot token.")
    ids = _text("DISCORD_ALLOWED_USER_IDS").split(",")
    if any(
        not re.fullmatch(r"[0-9]{1,20}", item.strip()) or not 1 <= int(item.strip()) <= 2**64 - 1
        for item in ids
    ):
        raise ConfigError("DISCORD_ALLOWED_USER_IDS requires a nonempty list of numeric user IDs.")
    command = _text("DISCORD_COMMAND_NAME", "ask")
    if not re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", command):
        raise ConfigError("DISCORD_COMMAND_NAME must be a lowercase slash command name.")
    model = _text("OLLAMA_MODEL")
    if not model or any(ord(c) < 32 or ord(c) == 127 for c in model):
        raise ConfigError("OLLAMA_MODEL must be an explicit nonblank model name.")
    try:
        timeout = float(_text("OLLAMA_TIMEOUT_SECONDS", "120"))
    except ValueError:
        raise ConfigError("OLLAMA_TIMEOUT_SECONDS must be a finite number from 1 to 600.") from None
    if not math.isfinite(timeout) or not 1 <= timeout <= 600:
        raise ConfigError("OLLAMA_TIMEOUT_SECONDS must be a finite number from 1 to 600.")
    keep_alive: str | int = _text("OLLAMA_KEEP_ALIVE", "0")
    if keep_alive == "0":
        keep_alive = 0
    else:
        match = re.fullmatch(r"([0-9]{1,4})(s|m)", keep_alive)
        if not match or not 1 <= int(match[1]) * (60 if match[2] == "m" else 1) <= 1800:
            raise ConfigError("OLLAMA_KEEP_ALIVE must be 0 or a positive s/m duration up to 30m.")
    think_value = _text("OLLAMA_THINK", "false").lower()
    if think_value not in {"false", "true", "auto"}:
        raise ConfigError("OLLAMA_THINK must be false, true, or auto.")
    num_ctx = _integer("OLLAMA_NUM_CTX", 2048, 512, 32768)
    num_predict = _integer("OLLAMA_NUM_PREDICT", 512, 1, min(4096, num_ctx))
    system = _text("LLM_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT)
    if not system or len(system) > 4000:
        raise ConfigError("LLM_SYSTEM_PROMPT must contain 1 to 4000 characters.")
    level = _text("LOG_LEVEL", "INFO").upper()
    if level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        raise ConfigError("LOG_LEVEL must be a standard Python logging level.")
    return Settings(
        discord_bot_token=token,
        allowed_user_ids=frozenset(int(item.strip()) for item in ids),
        command_name=command,
        ollama_base_url=_base_url(),
        ollama_model=model,
        ollama_keep_alive=keep_alive,
        ollama_think={"false": False, "true": True, "auto": None}[think_value],
        generation=GenerationSettings(timeout, num_ctx, num_predict),
        max_prompt_chars=_integer("MAX_PROMPT_CHARS", 1800, 1, 6000),
        max_concurrent_generations=_integer("MAX_CONCURRENT_GENERATIONS", 1, 1, 4),
        system_prompt=system,
        log_level=getattr(logging, level),
    )
