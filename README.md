# GoatLLM

Self-hosted text answers from local Ollama, invoked with `/ask` in a Discord group DM.
One friend's computer hosts GoatLLM and Ollama; other friends only need Discord and
access to the application. It is a user-installed Discord application, not a bot
member added to the group DM.

**Current status: planning and installable scaffold only.** `/ask`, configuration
validation, and the Ollama adapter are not implemented yet. `--help` and `--version`
work; running without arguments reports the missing runtime and exits with code 2.
The implementation sequence and acceptance criteria are in
[IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md).

## Development setup now

Python 3.12+ is required. This foundation was checked with Python 3.13 on Windows.
The intended repository is `GoatsSoftware/GoatLLM`; its existence/access has not been
confirmed, so use this folder until a clone URL is verified.

Windows PowerShell, from the project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m goatllm --help
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

Linux/macOS, from the project folder:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m goatllm --help
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
```

No activation script is required. Top-level dependencies are pinned in
`pyproject.toml`. `constraints-dev.lock` captures the resolved foundation environment;
use `pip install -c constraints-dev.lock -e '.[dev]'` to reproduce it. Platform-only
dependencies carry environment markers. This is a constraints snapshot, not a
hash-verified universal lock. Refresh deliberately alongside tests.

## Prepare the host for the upcoming runtime

These steps prepare external services; the application cannot answer commands yet.

1. Install [Ollama](https://ollama.com/download) yourself on the host. Keep its API on
   loopback (`127.0.0.1:11434`); do not expose it to the internet.
2. Choose and explicitly download a model, for example `ollama pull qwen3:1.7b`.
   This download is your choice; GoatLLM will never do it automatically.
3. Copy `.env.example` to `.env` (`Copy-Item .env.example .env` in PowerShell;
   `cp .env.example .env` on Linux/macOS). Add the bot token locally and the numeric
   Discord IDs allowed to invoke the application. Never paste secrets in commits,
   issue reports, or chat. The planned startup validator rejects an empty allowlist.
4. Follow [Discord setup](docs/DISCORD_SETUP.md) to create and install the application.
5. After milestones A-C are implemented, launch with `python -m goatllm` from your
   environment and stop with Ctrl+C. Run one active instance per Discord application.

Model starting points, verified against the Ollama library on 2026-10-30:

| Host | Start with | Notes |
| --- | --- | --- |
| CPU | [qwen3:0.6b](https://ollama.com/library/qwen3:0.6b) | Small trial; quality and latency vary. |
| 4 GB VRAM laptop | [qwen3:1.7b](https://ollama.com/library/qwen3:1.7b) | Conservative starting point; leave GPU/OS headroom. |
| 8 GB VRAM desktop | [qwen3:4b](https://ollama.com/library/qwen3:4b) | Start at 2,048 context tokens and one generation. |

These are starting sizes, not guaranteed fits or speed promises. Quantization,
context cache, other GPU applications, and CPU offloading affect memory and latency.
The model name stays configurable. Qwen3 supports thinking; the example requests
`think=false` to prioritize a final answer within a small token budget.

## Planned M1 behavior and privacy

`/ask prompt:<text>` sends only that prompt plus a configured system prompt to the
host's Ollama instance. GoatLLM will not read other messages or persist prompts,
answers, or conversation history. Logs will omit content, secrets, and personal IDs.
Discord and the host remain involved; this is not a promise of absolute privacy.

Authorization checks the invoker's numeric Discord ID. An allowed person can ask
in a conversation whose other members will see the answer. Everyone who needs to
invoke commands may need to install the application on their own account.

Successful answers will be public where Discord permits. M1 will edit one deferred
response, truncating overly long answers with an explicit notice. Mentions will be
disabled. Rejections before generation will be ephemeral. Discord server permissions
can constrain visibility; group DM behavior requires the live acceptance test.

Ollama local inference has no per-request paid API fee; hardware and electricity
still cost money. The defaults target modest resource use: one concurrent generation,
120-second deadline, 1,800 prompt characters, 512 generated tokens, 2,048 context
tokens, and `keep_alive=0`. Unloading after each response saves idle VRAM but adds
loading latency. A longer keep-alive trades idle memory for faster repeated requests.
Prompts near the character cap plus a large system prompt may exceed the token
context budget: characters are not tokens, and bounded context can truncate input.

## Project and next milestones

- [Architecture and lifecycle](docs/ARCHITECTURE.md)
- [Implementation tasks and validation matrix](docs/IMPLEMENTATION_PLAN.md)
- [Discord configuration and verified sources](docs/DISCORD_SETUP.md)
- [Manual group DM acceptance checklist](docs/MANUAL_TESTING.md)
- [Contribution workflow](docs/CONTRIBUTING.md)
- [Research and environment findings](docs/RESEARCH.md)

M1 is text only. Images/ComfyUI (M2), desktop packaging (M3), other providers, and
explicitly opt-in conversation context remain future work. No database, web UI,
Docker requirement, or agent framework is planned for M1.

MIT is the proposed license. The owner has not selected a license yet, so no
definitive license grant or ownership attribution has been added. Resolve this
before presenting the repository as licensed open source.
