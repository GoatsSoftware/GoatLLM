"""CLI and resource ownership. Imports never start Discord or Ollama."""

import argparse
import asyncio
import logging
import sys

import httpx

from goatllm import __version__
from goatllm.config import ConfigError, Settings, load_settings
from goatllm.discord_app import GoatClient
from goatllm.llm.ollama import OllamaProvider


def configure_logging(level: int) -> None:
    logger = logging.getLogger("goatllm")
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    logger.handlers[:] = [handler]
    logger.setLevel(level)
    logger.propagate = False
    # Dependency DEBUG and exception traces may include interaction tokens or IDs.
    for name in ("discord", "aiohttp", "httpx", "httpcore", "asyncio", "dotenv"):
        dependency = logging.getLogger(name)
        dependency.handlers[:] = [logging.NullHandler()]
        dependency.propagate = False
        dependency.setLevel(logging.CRITICAL + 1)


async def run(settings: Settings) -> None:
    async with httpx.AsyncClient(
        base_url=settings.ollama_base_url,
        trust_env=False,
        follow_redirects=False,
        limits=httpx.Limits(
            max_connections=settings.max_concurrent_generations,
            max_keepalive_connections=settings.max_concurrent_generations,
        ),
    ) as http_client:
        provider = OllamaProvider(
            http_client,
            model=settings.ollama_model,
            keep_alive=settings.ollama_keep_alive,
            think=settings.ollama_think,
        )
        async with GoatClient(settings, provider) as client:
            await client.start(settings.discord_bot_token)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="goatllm",
        description="Run the Discord user application backed by local Ollama.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.parse_args(argv)
    try:
        settings = load_settings()
    except ConfigError as error:
        print(f"Configuration error: {error}", file=sys.stderr)
        return 2
    configure_logging(settings.log_level)
    logger = logging.getLogger("goatllm")
    try:
        asyncio.run(run(settings))
    except KeyboardInterrupt:
        logger.info("shutdown_complete")
        return 0
    except Exception:
        logger.error("startup_or_connection_failed_check_token_network_and_app_configuration")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
