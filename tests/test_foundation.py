"""Offline checks for packaging, CLI, and import safety."""

import os
import subprocess
import sys


def test_cli_help_and_version() -> None:
    for argument in ("--help", "--version"):
        result = subprocess.run(
            [sys.executable, "-m", "goatllm", argument],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        assert result.returncode == 0
        assert "goatllm" in result.stdout.lower()


def test_unimplemented_runtime_exits_clearly() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "goatllm"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 2
    assert "not implemented yet" in result.stderr


def test_imports_have_no_network_or_configuration_side_effects() -> None:
    # Fresh process catches module-level side effects even when other tests imported them.
    script = """
import os
import socket
from unittest.mock import patch

def unexpected(*args, **kwargs):
    raise AssertionError('Import attempted network access or environment loading')

with patch.object(socket.socket, 'connect', unexpected), \
     patch('dotenv.load_dotenv', unexpected):
    import goatllm
    import goatllm.__main__
    import goatllm.config
    import goatllm.discord_app
    import goatllm.llm.base
    import goatllm.llm.ollama
assert 'DISCORD_BOT_TOKEN' not in os.environ
"""
    environment = {key: value for key, value in os.environ.items() if key != "DISCORD_BOT_TOKEN"}
    result = subprocess.run(
        [sys.executable, "-c", script],
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr
