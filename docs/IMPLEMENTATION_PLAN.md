# M1 implementation handoff

The owner authorized implementation after publishing the foundation. A-C are now
implemented and verified offline. The owner reported live `/ask` success on
2026-10-31 and selected MIT. D documentation/license are ready; remaining manual
scenarios are tracked in MANUAL_TESTING.md. M2/M3 remain out of scope.

## State at handoff

- [x] Read the original brief and audit the initially empty project folder.
- [x] Initialize local Git without creating a remote or publishing anything.
- [x] Research official Discord/Ollama APIs and pin available dependency versions.
- [x] Create installable `src/` package, CLI help/version, and provider contract.
- [x] Add offline dependency compatibility/import checks and documentation.
- [x] Finish A: runtime settings parser, validation, and tests.
- [x] B: working Discord -> Ollama -> Discord vertical slice.
- [x] C: resource limits, error hardening, shutdown, and boundary tests.
- [ ] D: user-ready documentation, review, and genuine group DM acceptance.

D documentation, the MIT license, and offline validation are ready. The remaining
gate is completion of the group DM visibility/failure/resource checklist.
Current evidence: 123 offline tests, Ruff lint/format, dependency validation, and
wheel installation smoke test pass on Windows/Python 3.13. CI adds Linux/Python 3.12.

The modules now contain the M1 runtime. Automated tests use HTTP mocks and fake
interactions; do not confuse offline success with real group DM acceptance.

## A: configuration and runtime foundation

Implement `ConfigError`, frozen/slotted `Settings`, and
`load_settings(env_file: Path | None = Path('.env')) -> Settings` in `config.py`.
Use `python-dotenv` with `override=False, interpolate=False` and UTF-8; load only
when called. Tests supply temporary files/isolated environment values. Do not search
parent directories for `.env`. `Settings` must have a redacted/disabled repr so tokens,
IDs, and system prompts never appear in diagnostics. Errors name fields and rules,
never their supplied values. Runtime configuration is immutable.

| Variable | Default | Validation / representation |
| --- | --- | --- |
| `DISCORD_BOT_TOKEN` | none | Required, strip outer whitespace; reject blank, sample `replace_me`, control/embedded whitespace; don't invent a token-format regex. Exclude from repr. |
| `DISCORD_ALLOWED_USER_IDS` | none | Required nonempty comma list of ASCII decimal positive integers, <= 2^64-1; reject empty elements/non-numeric IDs; deduplicate to `frozenset[int]`. No usernames/public-access flag. |
| `DISCORD_COMMAND_NAME` | `ask` | Conservative valid slash command name `[a-z][a-z0-9_-]{0,31}`. |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | HTTP only, host exactly `localhost`, `127.0.0.1`, or `::1`; valid port; root path only, no credentials/query/fragment. Normalize trailing slash; no network lookup. No remote opt-out in M1. |
| `OLLAMA_MODEL` | none | Required explicit model name; `.env.example` supplies `qwen3:1.7b`; reject blank/control characters. Never automatically pull or preload. |
| `OLLAMA_TIMEOUT_SECONDS` | `120` | Finite float 1-600 inclusive; absolute deadline in addition to HTTP timeouts. |
| `OLLAMA_KEEP_ALIVE` | `0` | Accept `0` or a positive integer duration suffixed `s`/`m`, up to 30 minutes; reject negatives/infinite residency. Adapter serializes `0` as numeric zero, other values as strings. |
| `OLLAMA_NUM_CTX` | `2048` | Integer 512-32768 inclusive; operator-selected budget, no GPU fit guarantee. |
| `OLLAMA_NUM_PREDICT` | `512` | Integer 1-4096 inclusive, <= `num_ctx`; never Ollama sentinel -1/-2. |
| `OLLAMA_THINK` | `false` | Parse `false`, `true`, or `auto`; auto omits `think`, false/true send booleans. Never expose thinking output. Example Qwen3 supports false. |
| `MAX_PROMPT_CHARS` | `1800` | Integer 1-6000 inclusive; validated again server-side even when command option has max_length. |
| `MAX_CONCURRENT_GENERATIONS` | `1` | Integer 1-4 inclusive; global admission counter, no queue. |
| `LLM_SYSTEM_PROMPT` | example's concise assistant text | Nonblank, <= 4000 characters; do not log. Characters do not ensure token fit. |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`; DEBUG must still omit content/IDs/secrets. |

Convert the portable limits to the existing `GenerationSettings` when wiring the
application. Leave model/keep-alive/thinking on the adapter. Friendly CLI validation
failure returns exit code 2 before opening network clients; unexpected runtime startup
failure returns 1 with a fixed safe message. Help/version return 0 without config.
No unnecessary `--check-config`, sync subcommand, packaging scripts, or config framework.

Acceptance: config tests cover defaults, env precedence, disabled dotenv expansion,
all invalid fields, finite bounds, loopback restrictions, secret-safe errors/repr,
and empty allowlist refusing startup. Re-run import safety and CLI help.

## B: vertical slice

1. Implement `OllamaProvider` with injected `httpx.AsyncClient`, model, keep-alive,
   and optional thinking bool. `generate` follows the existing protocol exactly.
   Shared client setup uses validated base URL, `trust_env=False`, no redirects, and
   bounded connection count. No SDK, discovery request, download, or startup inference.
2. `POST /api/chat`: `model`, `stream=false`, `messages` containing exactly system
   then user, `keep_alive`, `options.num_ctx`, `options.num_predict`, and `think`
   unless auto. No message history, tools, response streaming, or reasoning display.
3. Use `asyncio.timeout(generation_settings.timeout_seconds)` for the entire request
   and response read, plus httpx timeouts. For defensive response-size bounds,
   use an HTTP streamed response read with a 1 MiB cap, while the **Ollama protocol
   still uses `stream=false`**. Validate one JSON object, `done is True`, a `message`
   object, and nonblank string `content`; return only content. Ignore `thinking`.
   Missing/null/non-string content or backend `error` object is a classified failure.
4. Add the Discord client/build-command function. Receive a provider via injection.
   Apply verified USER_INSTALL and all three contexts. Parameter `prompt` should
   expose the configured max length with `app_commands.Parameter`/`Range` only if
   the installed API supports it; server-side validation is authoritative.
5. Implement authorization -> validation -> capacity reservation -> defer ->
   generation -> one response edit, as specified in ARCHITECTURE.md. Use fixed error
   text and `AllowedMentions.none()` at client construction and every send/edit.
6. Implement startup composition, global sync in setup_hook, and cleanup. Dedicated
   application owns its synced command set. Do not make live sync calls from tests.

| Failure | Classification | Discord text meaning |
| --- | --- | --- |
| Connection/DNS/network error | UNAVAILABLE | Host cannot reach its local model service. |
| asyncio deadline/httpx timeout | TIMEOUT | Request took too long; try again later. |
| HTTP 404 | MODEL_NOT_FOUND | Host needs to install/check its configured model. |
| Other non-2xx or JSON `error` | GENERATION_FAILED | Model could not complete; host should check resources/config. |
| Invalid JSON/schema/empty content/oversized body | INVALID_RESPONSE | Model returned an unusable answer. |

Never classify out-of-memory by matching arbitrary response text or show raw Ollama
errors. Do not log them either. HTTP redirects are errors rather than followed to
another host. Network errors and JSON exceptions become `ProviderError` with safe
codes; cancellation propagates. Catch unexpected callback failures at the Discord
boundary, log a fixed event, and attempt one safe error edit if acknowledged. Disable
discord.py's default callback traceback logging via explicit command error handling.

Acceptance: mocked `/api/chat` proves exact payload, no history, all failure
categories, and no leakage; mocked interaction proves defer before HTTP and one
public edit. The CLI is runnable with locally supplied credentials. Live test is
optional at this milestone if credentials/Ollama are still unavailable.

## C: robustness

- Finalize non-waiting admission. Test with an event-blocked fake provider: at N
  active calls, N+1 is immediately rejected; success/failure/cancellation/defer
  failure/edit failure all release capacity. No unbounded task spawning or retries.
- Render a single response <= 2,000 UTF-16 units; count emoji conservatively and
  truncate at a code-point boundary with `\n\n[Response truncated.]` within the cap.
  Prefer a nearby newline/space when convenient. Closing Markdown fences is optional;
  elaborate Markdown parsing is out of scope. Empty output maps to an error.
- Supply `AllowedMentions.none()` explicitly on every message path. Suppress link
  previews where API-supported. Test `@everyone`, `@here`, `<@123>`, and `<@&123>`.
- No interaction IDs, user IDs, channel IDs, raw exception strings, URLs containing
  interaction tokens, prompt text, outputs, or system prompts in logs. Test with
  sentinel content/secrets and caplog through success/error paths. Silence HTTP/Discord
  debug logging even if application LOG_LEVEL=DEBUG. Do not enable HTTPX tracing.
- Track and cancel outstanding handlers at shutdown before closing HTTP resources;
  test cancellation propagation and close order using fake clients. Ctrl+C exits
  cleanly; reconnect does not register duplicate commands or create clients repeatedly.
- Run provider absolute deadline test against a slowly progressing mocked response:
  httpx read inactivity timeout alone is insufficient to bound total wall time.

Tests to add alongside behavior (no empty placeholder test files):

| File | Evidence |
| --- | --- |
| `test_config.py` | Validation, privacy, dotenv precedence and bounds |
| `test_ollama.py` | MockTransport payload/schema/status/size/timeout/no-history |
| `test_discord_response.py` | Formatting, emoji limits, every reply's allowed_mentions |
| `test_discord_app.py` | Auth, order, busy behavior, capacity release, safe errors |
| `test_lifecycle.py` | Startup failure, resource closure, cancellation, sync once |

Use pytest-asyncio and `httpx.MockTransport`, plus unittest.mock/fake provider. No
additional HTTP mock dependency is needed. Test behavior and error paths; avoid tests
that merely restate field assignments. Keep the existing installed-API check until
its assertions can exercise the real command factory.

## D: shareable delivery

1. Replace scaffold warnings with the tested runtime status. Complete launch/stop,
   dependency/clone instructions, model profiles, resource tuning, privacy, and
   troubleshooting. Preserve the distinction between host and Discord clients.
2. Run the full offline suite once, `ruff check .`, `ruff format --check .`,
   `pip check`, and a wheel build/install smoke check as appropriate. Update only
   dependencies requiring a justified change. Record Python/OS actually tested;
   do not claim Linux or Python 3.12 execution without evidence.
3. Execute [MANUAL_TESTING.md](MANUAL_TESTING.md) on a real group DM with human-provided
   credentials and local Ollama. Never mark unrun steps passed or download a model
   without the owner's choice. If blocked, deliver the code and clearly mark M1
   live acceptance pending instead of claiming completion.
4. Review the Git diff for secrets/unrelated files; create coherent local commits
   if Git identity is available. Verify remote existence and authenticated write
   access before any remote operation. The owner authorized ordinary commits/PR
   work and publication to the public GoatsSoftware/GoatLLM repository. Selecting
   the MIT license was subsequently approved by the owner on 2026-10-31.
5. Preserve the approved MIT LICENSE and its package metadata when distributing.

## Definition of done and human dependencies

M1 succeeds when an allowlisted friend invokes `/ask` in a real group DM, all
participants can see the Ollama-generated answer, failures do not kill the host,
resource bounds hold, and GoatLLM persists no conversation content. Passing offline
tests alone is insufficient to claim that live milestone.

Initial live prerequisites: Ollama installed/running and a chosen downloaded
model; a dedicated configured Discord application/token; at least two test accounts
and a group DM, including a second allowed user to prove shared capacity and a
denied user to prove authorization. Keep secrets/IDs in ignored local config.
GitHub authentication and public repository publication are complete. The runtime
was launched successfully by the owner after local Discord/Ollama configuration.
Continue the remaining manual checklist without treating the basic success report
as evidence that all multi-user, failure, and GPU checks have passed.
