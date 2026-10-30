# Contributing

Start with [README](../README.md), [the original brief](../GoatLLM_Codex_Brief.md), and
[the implementation plan](IMPLEMENTATION_PLAN.md). Keep contributions within text-only
M1 until its live acceptance succeeds. The owner has not selected a license yet.

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
current suite only verifies the foundation; add behavior tests with implementation.

Review `git diff` and `git status --short` before committing named files. Never stage
`.env`, credentials, real user IDs, model weights, or transcript files. Make small,
coherent commits; describe behavior and validation in a PR. Avoid blanket dependency
updates and unsolicited architecture/framework changes.

Once the actual repository and your write access are confirmed, the normal workflow
is a feature branch, push, PR, review, merge. Example future commands:

```bash
git remote add origin https://github.com/GoatsSoftware/GoatLLM.git
git push -u origin feature/short-description
gh pr create --base main --fill
```

These commands are documentation, not actions already performed. Verify the remote
first; the initial public probe returned 404, and local `gh` authentication was invalid.
Do not create an organization repository merely to make these commands work.

Runtime safety: keep imports inert, use provider injection, await resource cleanup,
use fixed safe error messages, and disable mentions on every reply. No real interaction
payload fixtures with tokens or personal IDs. Do not expose debug traces to Discord.
