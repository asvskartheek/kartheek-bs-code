# CLAUDE.md

## Project Overview

This is a Python project managed with [uv](https://docs.astral.sh/uv/).

## Setup

Install uv (if not already installed):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Install dependencies and create virtual environment:
```bash
uv sync
```

## Common Commands

| Task | Command |
|------|---------|
| Run the project | `uv run python main.py` |
| Add a dependency | `uv add <package>` |
| Add a dev dependency | `uv add --dev <package>` |
| Remove a dependency | `uv remove <package>` |
| Run tests | `uv run pytest` |
| Run a script | `uv run <script>` |
| Update dependencies | `uv sync --upgrade` |

## Project Structure

```
.
├── main.py              # Entry point (includes Phoenix startup check)
├── start_phoenix.sh     # Start the Phoenix observability server
├── pyproject.toml       # Project metadata and dependencies
├── uv.lock              # Locked dependency versions (do not edit manually)
├── .venv/               # Virtual environment (gitignored)
├── .env -> /Users/yashwanthseelam/kartheek_bs_code/.env  # Symlink to canonical secrets (gitignored)
├── .gitignore
├── README.md
└── CLAUDE.md            # This file
```

### `.env` across worktrees

The canonical `.env` lives at `~/kartheek_bs_code/.env` (never committed). Each worktree's `.env` is a symlink to it. When creating a new worktree, run:
```bash
ln -sf ~/kartheek_bs_code/.env .env
```

### `pre-commit` hook across worktrees

The `.git/hooks/pre-commit` script hardcodes an absolute path to the Python that installed it. If a new worktree runs `uv sync`, that worktree's venv becomes the active one — but the hook still points to wherever it was last installed from, causing `` `pre-commit` not found `` errors on commit.

**RULE: After creating any new worktree, re-anchor the hook to the main worktree:**
```bash
cd ~/kartheek_bs_code && uv run pre-commit install
```

Never run `pre-commit install` from inside a worktree — always run it from the main worktree so the hook path stays stable.

## Observability (Phoenix Tracing)

**RULE: Before writing any code or working on any task, the Phoenix observability server MUST be running.**

**RULE: Phoenix MUST always be started from the main worktree (`~/kartheek_bs_code`), never from inside a worktree.**

Start Phoenix first:
```bash
cd ~/kartheek_bs_code && bash start_phoenix.sh &
```

Then verify the UI is up (not just the healthcheck) at: http://localhost:6006

### Why the main worktree only

Each worktree has its own `.venv` and may have a different version of `arize-phoenix` installed. If Phoenix is started from a worktree venv, it may be a different version than the one the current worktree's code sends traces to. This causes the Phoenix UI to return **Internal Server Error** on every page — even though `/healthz` still returns `OK` (the healthcheck does not catch version mismatches).

### Diagnosing a stale/wrong-worktree Phoenix process

If you see Internal Server Error in the Phoenix UI:

```bash
# 1. Find the offending process
ps aux | grep phoenix | grep -v grep

# 2. Check which worktree it came from (look for /worktrees/<id>/ in the path)
# 3. Kill it and restart from the main worktree
kill <PID>
cd ~/kartheek_bs_code && bash start_phoenix.sh &
```

Phoenix traces all LangChain/LLM calls. If Phoenix is not running, `main.py` will fail to export spans.

## Documentation (Pre-Review Gate)

**RULE: Before any code is ready for human review, you MUST:**

1. **Add detailed docstrings** to every new or modified module, function, class, and method using Google style. Include `Args:`, `Returns:`, `Raises:`, and a usage `Example::` where helpful.

2. **Rebuild the MkDocs site** to verify the docs render without errors:
   ```bash
   uv run mkdocs build
   ```

These are not optional polish steps — they are a hard gate before review. Code without docstrings or with a broken docs build should not be submitted for review.

---

## Development Notes

- Python version requirement: >=3.9 (see `pyproject.toml`)
- Do not manually edit `uv.lock`; it is managed by `uv`
- Always use `uv run` to execute scripts so the correct venv is used
- Add secrets to `.env` (gitignored); use `.env.example` for templates
