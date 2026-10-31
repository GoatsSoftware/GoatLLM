# Contributing

Start with [README](../README.md), [the original brief](../GoatLLM_Codex_Brief.md), and
[the implementation plan](IMPLEMENTATION_PLAN.md). Keep contributions within text-only
M1 while its remaining manual checks are completed. The project uses the MIT
license; preserve the notice in LICENSE when distributing copies.

Create a virtual environment and install `-e '.[dev]'` as shown in the README.
Use Python 3.12+ and avoid global package installs. Tests use mocks and must not need
a Discord token, a running Ollama server, or a GPU. Never run live command sync from
the automated suite.

```bash
git switch -c feature/short-description
python -m pytest
python -m ruff check .
python -m ruff format --check .
```

Use your environment's Python path if the venv is not activated. Run focused tests
while developing, and the full offline suite before delivering a milestone. The
suite covers configuration, provider failures, Discord safety, and lifecycle. Add
behavior tests alongside changes; leave live tests in the manual checklist.

Review `git diff` and `git status --short` before committing named files. Never stage
`.env`, credentials, real user IDs, model weights, or transcript files. Make small,
coherent commits; describe behavior and validation in a PR. Avoid blanket dependency
updates and unsolicited architecture/framework changes.

The public repository is https://github.com/GoatsSoftware/GoatLLM. Use a feature
branch and a PR for normal contributions:

```bash
git push -u origin feature/short-description
gh pr create --base main --fill
```

If GitHub CLI appears unauthenticated only inside a restricted Windows sandbox,
check from the user's terminal before resetting working credentials. Git ownership
checks can also differ between the sandbox account and the host account; prefer a
command-scoped safe.directory for this exact workspace over disabling checks globally.

Runtime safety: keep imports inert, use provider injection, await resource cleanup,
use fixed safe error messages, and disable mentions on every reply. No real interaction
payload fixtures with tokens or personal IDs. Do not expose debug traces to Discord.
