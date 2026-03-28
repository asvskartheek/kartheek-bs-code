# kartheek-bs-code

A LangChain-powered travel assistant agent that answers weather questions using a simulated weather tool, with full Phoenix observability tracing and an automated evaluation harness.

## What it does

- Accepts natural-language weather questions (e.g. *"What is the weather in Tokyo?"*).
- Routes the query through a **DeepAgent** backed by `gpt-4o-mini` via OpenRouter.
- The agent calls the `get_weather` tool, which returns a simulated condition and temperature.
- Every LLM call and tool invocation is traced in **Phoenix** (Arize) for observability.
- An **eval harness** (`eval.py`) measures tool-call correctness and response quality using Phoenix Experiments.

## Quick start

```bash
# 1. Install dependencies
uv sync

# 2. Set your OpenRouter API key
echo "OPENROUTER_API_KEY=sk-or-..." >> .env

# 3. Start the Phoenix observability server
bash start_phoenix.sh &

# 4. Run the demo
uv run python main.py

# 5. Run evals
uv run python eval.py
```

Phoenix UI: [http://localhost:6006](http://localhost:6006)

## Project layout

```
.
├── agent.py        # Weather tool + agent factory
├── main.py         # Demo entry point with Phoenix tracing
├── eval.py         # Phoenix evaluation harness
├── start_phoenix.sh
├── pyproject.toml
└── docs/           # This documentation site
```
