> **Completely built on Cline Kanban**

# kartheek-bs-code

A Python-based AI agent project with full LLM observability, evals, and deep agent support — built using [uv](https://docs.astral.sh/uv/) for dependency management.

## What's Inside

### Agent (`agent.py`)
A weather travel assistant built with [LangChain](https://www.langchain.com/) and [DeepAgents](https://pypi.org/project/deepagents/), routed through [OpenRouter](https://openrouter.ai/) using `gpt-4o-mini`. The agent has access to a `get_weather` tool and answers natural language questions about weather in any city.

### Observability (`main.py` + Phoenix)
All LLM calls are traced via [Arize Phoenix](https://phoenix.arize.com/), an open-source LLM observability platform. Before running anything, the Phoenix server must be up:

```bash
bash start_phoenix.sh &
```

Then open: [http://localhost:6006](http://localhost:6006)

### Evals (`eval.py`)
A Phoenix-native eval harness with co-located datasets and evaluators:
- **Code evaluator** — checks if the agent called `get_weather` with the correct city
- **LLM-as-judge evaluator** — checks if the agent responded directly without asking follow-up questions

Run evals:
```bash
uv run python eval.py
# or with a specific dataset:
uv run python eval.py --dataset dev-time-data
```

## Setup

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Add your secrets
cp .env.example .env   # then fill in OPENROUTER_API_KEY

# Start Phoenix
bash start_phoenix.sh &

# Run the agent
uv run python main.py
```

## Stack

| Layer | Tool |
|---|---|
| Package manager | [uv](https://docs.astral.sh/uv/) |
| LLM routing | [OpenRouter](https://openrouter.ai/) |
| Agent framework | [DeepAgents](https://pypi.org/project/deepagents/) + LangChain |
| Observability | [Arize Phoenix](https://phoenix.arize.com/) |
| Evals | Phoenix Experiments |
| Formatting | [Black](https://black.readthedocs.io/) |
| Pre-commit hooks | [pre-commit](https://pre-commit.com/) |

## Requirements

- Python >=3.11, <3.14
- `OPENROUTER_API_KEY` in your `.env`
