# Initial feasibility and environment audit

Date: 2026-10-30 (Europe/Paris). This records evidence for the planning handoff.

## Local findings

- Initial folder: only `GoatLLM_Codex_Brief.md`; no existing Git history, source,
  local AGENTS instructions, `.env`, or credentials found in this folder.
- Parent AGENTS paths checked through the workspace ancestry; none found.
- Git 2.54.0.windows.1 available; initialized a new local `main` repository.
- Python 3.13.14 is on PATH. `py --list` did not enumerate installed runtimes;
  use `python`, not a presumed `py -3.12` command. Python 3.12 is the package minimum.
- Created project-local `.venv`; no global package installation required.
- Ollama executable not found on PATH; service/model/GPU availability untested.
- GitHub CLI is installed but `gh auth status` reports an invalid saved token.
- Unauthenticated GitHub API probe for `GoatsSoftware/GoatLLM` returned 404. This
  means absent or inaccessible to that probe; it does not prove the repository is
  absent. No remote write access verified and no remote repository created.
- No connected GitHub/Discord tools were available in this session. GitHub CLI can
  be used after authentication. Live Discord use requires app credentials/setup.
- Git identity was not configured in the initial environment; local commit creation
  must not invent the owner's author name or email.

## Versions selected

PyPI JSON metadata was queried directly to verify available versions before pinning:

| Package | Pin | Role |
| --- | --- | --- |
| discord.py | 2.7.1 | Gateway and application commands |
| httpx | 0.28.1 | Async Ollama HTTP client |
| python-dotenv | 1.2.4 | Explicit local env loading |
| pytest | 9.2.0 | Offline tests |
| pytest-asyncio | 1.4.1 | Async tests |
| ruff | 0.17.3 | Simple lint/format |
| setuptools | 84.2.1 | Build backend |

Resolved transitive dependencies are captured in `constraints-dev.lock`; runtime
has only three direct dependencies. No voice extras, agent SDK, Docker, GPU Python
libraries, or Ollama SDK needed.

## API feasibility and decisions

- Discord officially supports user-installed commands in private channels. The
  installed discord.py decorators serialize USER_INSTALL and PRIVATE_CHANNEL.
  `tests/test_discord_compatibility.py` verifies the installed behavior offline.
- Gateway interactions are an officially supported delivery mechanism, mutually
  exclusive with an application interaction webhook endpoint. Choose Gateway for a
  host PC without inbound networking. Built-in heartbeats/reconnection are expected;
  do not add an application polling loop.
- Public responses are subject to Discord context and permissions. The M1 acceptance
  test must prove visible group DM output; offline serialization cannot prove that.
- Ollama documents non-streaming `/api/chat`, generation options, keep_alive, and
  separate content/thinking fields. Explicitly use `stream=false` and display only
  content. Add a small thinking setting because Qwen3 can spend a short generation
  budget entirely on reasoning before producing an answer.
- Library model tags `qwen3:0.6b`, `qwen3:1.7b`, and `qwen3:4b` were found. These are
  configurable examples, not downloads or measured hardware recommendations.

## Foundation validation results

Executed on Windows with the project-local Python 3.13.14 environment:

- `pip install --no-build-isolation -e ".[dev]"`: editable package installed.
- `python -m pytest -q`: **5 passed**; CLI help/version, honest scaffold exit,
  inert imports, installed Discord command serialization, and disabled mentions.
- `python -m ruff check .`: passed.
- `python -m ruff format --check .`: passed.
- `python -m pip check`: no broken requirements.
- `python -m pip wheel --no-deps --no-build-isolation --wheel-dir dist .`:
  built `goatllm-0.1.0.dev0-py3-none-any.whl` successfully; local build output ignored.
- Generated 27 resolved constraints with platform markers for colorama/audioop-lts.

These checks validate the foundation only. No live Discord registration, group DM,
Ollama inference, GPU behavior, Linux run, or Python 3.12 run has been performed.
No GitHub publication or commit was made; Git author identity remains unset.

## Primary references

- [Discord installation/context tutorial](https://docs.discord.com/developers/tutorials/developing-a-user-installable-app)
- [Discord application commands](https://docs.discord.com/developers/interactions/application-commands)
- [Discord interaction response deadlines and delivery](https://docs.discord.com/developers/interactions/receiving-and-responding)
- [discord.py interaction API](https://discordpy.readthedocs.io/en/stable/interactions/api.html)
- [discord.py package metadata](https://pypi.org/project/discord.py/)
- [Ollama chat API](https://docs.ollama.com/api/chat)
- [Ollama thinking controls](https://docs.ollama.com/capabilities/thinking)
- [Ollama model library: Qwen3 0.6B](https://ollama.com/library/qwen3:0.6b),
  [1.7B](https://ollama.com/library/qwen3:1.7b), [4B](https://ollama.com/library/qwen3:4b)
