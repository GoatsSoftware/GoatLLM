# GoatLLM implementation guidance

Read `GoatLLM_Codex_Brief.md`, `docs/IMPLEMENTATION_PLAN.md`, and
`docs/ARCHITECTURE.md` before changing runtime behavior. The user's latest explicit
request takes precedence over the original brief. The initial batch deliberately
stops at an installable planning scaffold; runtime milestones A-D remain to implement.

- Python 3.12+, src layout, discord.py user installation/private-channel commands,
  local Ollama only, stateless text-only M1. No web frontend or database.
- Keep Discord independent of Ollama HTTP transport through `LLMProvider`.
- Never load .env, open network connections, or configure logging during import.
- Validate startup configuration and fail closed for an empty user allowlist.
- Never log or commit tokens, prompts, outputs, system prompts, or personal IDs.
- Defer admitted interactions immediately, disable mentions, bound work and output,
  reject when busy without queueing, and release resources on every exit path.
- Do not download models automatically. Do not claim live Discord/GPU verification
  based on offline tests. Record outstanding live checks honestly.
- Use `.venv/Scripts/python.exe` in this Windows workspace; `python` is 3.13 on PATH.
  Run focused pytest tests after changes and full pytest/Ruff at delivery milestones.
- GitHub auth was invalid at audit; verify before remote operations. No definitive
  license was chosen. Do not invent Git author identity or a copyright owner.
- Preserve the original brief. Keep implementation state in the plan current as
  each milestone completes; do not expand into M2/M3.
