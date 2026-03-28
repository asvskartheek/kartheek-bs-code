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

## Observability (Phoenix Tracing)

**RULE: Before writing any code or working on any task, the Phoenix observability server MUST be running.**

Start Phoenix first:
```bash
bash start_phoenix.sh &
```

Then verify it's up at: http://localhost:6006

Phoenix traces all LangChain/LLM calls. If Phoenix is not running, `main.py` will fail to export spans. Check `start_phoenix.py` for details.

---

## Development Notes

- Python version requirement: >=3.9 (see `pyproject.toml`)
- Do not manually edit `uv.lock`; it is managed by `uv`
- Always use `uv run` to execute scripts so the correct venv is used
- Add secrets to `.env` (gitignored); use `.env.example` for templates
