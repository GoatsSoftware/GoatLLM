# Live M1 acceptance checklist

Status: **not executed**. The runtime is implemented; credentials and local Ollama setup are still needed.
Record actual OS, Python, discord.py, Ollama version, model tag/quantization, and date
when testing. Keep tokens and personal Discord IDs out of results/screenshots.

## Preconditions

- [x] Offline tests pass and runtime milestones A-C are implemented.
- [ ] One host runs Ollama on loopback and has the explicitly selected model.
- [ ] Dedicated Discord app supports User Install; no webhook interaction endpoint.
- [ ] Host's ignored `.env` contains valid token and at least two authorized users.
- [ ] Application installed on invoking accounts; real group DM includes test friends.
- [ ] Only one GoatLLM process uses the application token.

## Required checks

| Check | Expected outcome | Result |
| --- | --- | --- |
| Start host with valid configuration | Gateway ready, global command sync, no prompt/model preload | Pending |
| Invoke `/ask` in group DM | Prompt acknowledged promptly; final answer visible to other members | Pending |
| Invoke from a second allowed account | Same host answers without client-side Python/Ollama | Pending |
| Invoke from installed but denied account | Private rejection; no Ollama generation | Pending |
| Submit blank/over-limit prompt | Client or private server-side rejection; host stays up | Pending |
| Second allowed request while busy | Immediate private busy message; no growing queue | Pending |
| Prompt requesting long output | One message, explicit truncation within limit | Pending |
| Prompt requesting mentions | Literal text possible, no notifications from everyone/here/users/roles | Pending |
| Stop Ollama, then invoke | Friendly error, process survives, capacity released | Pending |
| Configure unavailable model | Friendly model/config error, no automatic pull | Pending |
| Use a short timeout with slow inference | Bounded failure; subsequent requests can be handled | Pending |
| Inspect normal and error logs | No prompts, output, system prompt, tokens, or personal IDs | Pending |
| Ask a follow-up referring to prior prompt | No prior prompt passed to provider; no history retained | Pending |
| Interrupt host during generation | Ctrl+C exits cleanly, no unclosed HTTP session warnings | Pending |
| Restart host | No retained conversation state; command remains usable | Pending |
| Check model residency with `keep_alive=0` | Idle model unload observed; explain possible load latency | Pending |

A model's answer alone cannot prove statelessness: use offline payload tests and
code inspection for that property. Similarly, log inspection supplements automated
sentinel tests. Do not claim immediate backend GPU cancellation merely because the
client request timed out.

Secondary contexts: test a DM with the app and a guild channel that allows external
apps. Record restrictions honestly; mandatory success is the group DM path.
No permission prompts should require inviting a bot member into the group DM.

Do not deliberately exhaust GPU memory. Provider tests exercise backend error
responses safely; an incidental memory failure should give a generic friendly error.
