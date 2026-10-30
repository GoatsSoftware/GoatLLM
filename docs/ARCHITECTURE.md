# M1 architecture

Status: design frozen for the next implementation batch; only the CLI scaffold,
provider contract, packaging, and offline compatibility checks exist today.

## Boundaries

```text
Discord client (friend)
  -> Discord interactions -> Gateway connection on the host
  -> discord_app.py: authorization, validation, admission, defer
  -> LLMProvider.generate(prompt, system_prompt, GenerationSettings)
  -> OllamaProvider -> shared httpx.AsyncClient -> loopback Ollama /api/chat
  <- final answer text <- one safe edit_original_response
```

The host makes outbound Discord connections. There is no HTTP listener, public
callback endpoint, tunnel, passive message listener, or message-content intent.
Discord transport uses `discord.Client` with `Intents.none()` and a `CommandTree`.
The application uses a bot token to authenticate the Gateway, while friends install
commands on their user accounts with `applications.commands`.

| Module | Responsibility |
| --- | --- |
| `__main__.py` | CLI, explicit configuration loading, safe logging, async lifecycle |
| `config.py` | Frozen settings and field-only validation errors |
| `discord_app.py` | Build command, global sync, request admission, replies, rendering |
| `llm/base.py` | `LLMProvider`, `GenerationSettings`, classified safe errors |
| `llm/ollama.py` | Ollama request/response mapping and transport error classification |

No service/repository/manager hierarchy is needed. The provider accepts plain text
and generation settings; Discord sees no HTTP response or Ollama-specific exception.
The composition root owns the HTTP client and injects it into the adapter. Model,
keep-alive, and thinking policy are adapter configuration, not Discord concerns.

## One request

1. Check numeric invoker ID, nonblank prompt, and configured length in memory.
   Reject immediately with an ephemeral message when invalid.
2. If all generation slots are occupied, reject ephemerally without queueing.
   Reserve a slot by incrementing a counter without an intervening `await`; all
   callbacks share one asyncio event loop. Never wait on a semaphore to enter a queue.
3. Within a `try/finally`, immediately `defer(thinking=True, ephemeral=False)`.
   No Ollama HTTP call precedes successful acknowledgment. If defer fails, skip
   inference and release the slot.
4. Await provider generation under an absolute asyncio deadline; include connection,
   model load, and response reading. Default 120s; configured ceiling 600s leaves
   margin under Discord's 15-minute token lifetime.
5. Validate text, render to at most 2,000 UTF-16 code units including a truncation
   notice, and edit the original response with `AllowedMentions.none()` explicitly.
   Use one message; do not send the entire output as multiple follow-ups or a file.
6. Map failures to fixed, friendly text. After a public defer, errors share that
   response's visibility. Never try to change it to ephemeral afterward.
7. Release the slot on success, timeout, cancellation, failed defer, or failed edit.

An authorization failure never reaches the provider. Capacity is global to the
instance. A timeout releases application capacity; it cannot prove immediate
server-side GPU cancellation. Keep the Ollama host private and document that a
generation might finish briefly after a disconnected request. No automatic retries.
Per-user rate limiting is deferred until observed use justifies it.

## Startup and shutdown

The future CLI parses arguments first, so help/version never require credentials.
Load `.env` from the working directory explicitly, with environment variables taking
precedence and interpolation disabled. Validate before network access. Configure a
content-free application logger and suppress verbose dependency logs; do not call
`Client.run()` with its default logging setup or log exception representations.

`asyncio.run(run(settings))` owns a shared `AsyncClient(trust_env=False,
follow_redirects=False)` and the Discord client in async context managers.
`setup_hook()` adds the one global command and syncs once per login, never from
`on_ready()` (which runs again on reconnect). Sync failure prevents normal startup.
Command sync reconciles this app's command set; use a dedicated Discord application.
Reconnect uses discord.py defaults and does not start duplicate clients.

Track active handler tasks in the Discord client. On shutdown, stop admission,
cancel and await active tasks, close the Gateway, then close HTTP resources. Handle
Ctrl+C without a traceback. Do not suppress `CancelledError` inside provider code.
Imports perform no environment loading, logger initialization, or network operations.

## Privacy and extension policy

No prompt cache, database, local transcript, prompt-based metrics, or external
telemetry. Logs use safe event names and error classifications only; no IDs, URLs
with interaction tokens, backend response bodies, or stack traces containing inputs.
Treat LLM output as untrusted display text; disable mentions and link previews where
the installed API supports it. Never execute tool calls or shell commands.

M1's provider protocol is the seam for a future second text backend. Images need
their own module and result type later. Streaming, GUI packaging, and opt-in context
must preserve a maintainable stateless text path. No placeholder media modules now.
