# GoatLLM

Self-hosted text answers from local Ollama, invoked with `/ask` in a Discord group DM.
One friend's computer hosts GoatLLM and Ollama; other friends only need Discord and
access to the application. This is a user-installed Discord application, not a bot
member added to the group DM.

**Status: M1 text runtime implemented and tested offline; real Discord/Ollama
acceptance remains pending.** See [manual testing](docs/MANUAL_TESTING.md).

## Install

Python 3.12+ is required. Development checks ran on Windows with Python 3.13.
Skip cloning if you already have this folder. No activation script is required.

Windows PowerShell:

```powershell
git clone https://github.com/GoatsSoftware/GoatLLM.git
Set-Location GoatLLM
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m goatllm --help
```

Linux/macOS:

```bash
git clone https://github.com/GoatsSoftware/GoatLLM.git
cd GoatLLM
python3 -m venv .venv
.venv/bin/python -m pip install -e .
cp .env.example .env
.venv/bin/python -m goatllm --help
```

## Configure and run

1. Install [Ollama](https://ollama.com/download) yourself on the host. Keep its API
   on loopback (`127.0.0.1:11434`); do not expose it to the internet.
2. Choose and explicitly download a model, for example `ollama pull qwen3:1.7b`.
   GoatLLM never downloads or preloads models automatically.
3. Follow [Discord setup](docs/DISCORD_SETUP.md): create a dedicated application,
   enable User Install with `applications.commands`, leave privileged intents and
   the Interactions Endpoint URL disabled, and install it on invoking accounts.
4. Edit your local `.env`: set `DISCORD_BOT_TOKEN`, comma-separated numeric
   `DISCORD_ALLOWED_USER_IDS`, and the exact `OLLAMA_MODEL` tag. Empty allowlists,
   placeholder tokens, unsafe URLs, and unbounded resource settings fail startup.
   Never share tokens in chat, commits, issues, or screenshots.
5. Ensure Ollama is running. Its Windows app normally provides the local service;
   run `ollama serve` separately if your installation does not start it automatically.
6. Launch one GoatLLM instance for that Discord application; stop with Ctrl+C.

```powershell
# Windows, from the project folder after editing .env:
.\.venv\Scripts\python.exe -m goatllm
```

```bash
# Linux/macOS:
.venv/bin/python -m goatllm
```

Wait for `commands_synced` and `discord_ready`, then try `/ask prompt:Hello` in a
real group DM. Global commands may need propagation/client refresh time. One host
serves all authorized friends; friends do not each run GoatLLM or Ollama for the
same application. Contributors running their own host should create a separate
Discord application/token. Global sync owns this app's command set, so use a
dedicated application rather than sharing an existing bot's token.

Environment variables override `.env`. File values such as `${VARIABLE}` stay
literal. Start from the folder containing `.env`; parent folders are not searched.
All fields/defaults/bounds are in the [configuration table](docs/IMPLEMENTATION_PLAN.md).
`--help` and `--version` do not load credentials or access the network.

## Model and resource choices

Starting points verified against the Ollama library on 2026-10-30:

| Host | Start with | Notes |
| --- | --- | --- |
| CPU | [qwen3:0.6b](https://ollama.com/library/qwen3:0.6b) | Small trial; quality and latency vary. |
| 4 GB VRAM laptop | [qwen3:1.7b](https://ollama.com/library/qwen3:1.7b) | Conservative starting size; leave GPU/OS headroom. |
| 8 GB VRAM desktop | [qwen3:4b](https://ollama.com/library/qwen3:4b) | Start with a small context and one generation. |

These are starting sizes, not guaranteed fits or speed promises. Quantization,
context cache, other GPU applications, and CPU offloading affect memory and latency.
No model name is hardcoded in the provider. The example uses Qwen3 with
`OLLAMA_THINK=false` to prioritize final text; `auto` omits that option for another
model. Thinking traces are never displayed. If the model cannot disable thinking,
a short generation budget can produce no final answer and will be rejected.

Defaults: one concurrent generation, a 120-second absolute deadline, 1,800 prompt
characters, 512 generated tokens, 2,048 context tokens, and `keep_alive=0`.
Unloading after each response saves idle VRAM but adds loading latency. Positive
keep-alive values up to 30 minutes trade idle memory for faster repeated requests.
Ollama local inference has no per-request paid API fee; hardware/electricity still
cost money. Prompt/system-prompt character limits do not guarantee token fit;
a large prompt can exceed the context budget and be truncated by the model service.

## Behavior and privacy

Only the current prompt plus the configured system prompt reaches the host's Ollama
instance. GoatLLM does not passively read other messages or persist prompts, answers,
or conversation history. Logs omit content, tokens, system prompts, and personal IDs,
even at DEBUG. Discord and the host remain involved; this is not absolute privacy.

Access uses the invoker's numeric ID, not their username. Installing the application
alone does not grant access. An allowed person can ask in a conversation whose other
members will see the answer, even if those members are not on the allowlist.

Accepted requests defer immediately and edit one public response where Discord
permits. Overlong answers are truncated within 2,000 UTF-16 units with an explicit
notice. Mentions are disabled on every reply; literal mention text may still appear.
Ordinary links can show Discord previews because the pinned original-response edit
API has no preview-suppression option. No shell commands or model tool calls execute.

Rejections before generation are ephemeral. Errors after a public defer share its
visibility. Busy requests are rejected rather than queued. No automatic retries.
Guild permissions can constrain public replies; the group DM path remains the
mandatory live acceptance check. A timed-out/disconnected client request does not
prove immediate backend GPU cancellation: Ollama may finish work briefly afterward.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Configuration error, exit 2 | Named field in `.env`; model/token/nonempty allowlist required. Check overriding shell variables. |
| Startup/connection failure, exit 1 | Internet access, bot token, app configuration, and global command sync permissions. |
| Missing `/ask` | User Install, account installation, PRIVATE_CHANNEL, global sync, client refresh; see Discord setup. |
| Cannot reach Ollama | Start the service and verify local host/port. Do not expose port 11434 publicly. |
| Model unavailable | Check `ollama list`; explicitly pull your chosen tag and match it in `.env`. |
| Generation failed | Host checks model compatibility/memory. Try a smaller model/context; backend details are withheld. |
| Timeout | Try a smaller model or answer budget; deadline can be raised to at most 600 seconds. |
| Host busy | Try again after the active generation finishes; there is no waiting queue. |
| Unusable/empty answer | Check thinking settings and generation budget; malformed backend responses are rejected. |

## Development

Install tools with `python -m pip install -e '.[dev]'`, then use your venv Python:

```bash
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

Tests use HTTP mocks and fake interactions, with no production token, Ollama service,
or GPU needed. In a restricted Windows environment use pytest's
`--basetemp .pytest_cache/tmp` if the usual temporary directory is inaccessible.

Direct dependencies are pinned in `pyproject.toml`. `constraints-dev.lock` captures
the resolved dev environment; reproduce with
`python -m pip install -c constraints-dev.lock -e '.[dev]'`. Platform-only packages
carry environment markers. This is a constraints snapshot, not a hash-verified
universal lock. Refresh intentionally alongside tests.

- [Architecture and lifecycle](docs/ARCHITECTURE.md)
- [Implementation plan and configuration](docs/IMPLEMENTATION_PLAN.md)
- [Discord setup and official sources](docs/DISCORD_SETUP.md)
- [Manual group DM acceptance checklist](docs/MANUAL_TESTING.md)
- [Contributing](docs/CONTRIBUTING.md)
- [Research and validation record](docs/RESEARCH.md)

M1 is text only. Images/ComfyUI (M2), desktop packaging (M3), additional providers,
and explicitly opt-in conversation context remain future work. No database,
frontend, Docker requirement, or agent framework in M1.

MIT is proposed; the owner has not selected a license, so no definitive grant or
copyright attribution has been added. Resolve this before advertising the project
as licensed open source.
