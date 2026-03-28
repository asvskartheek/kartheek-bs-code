# Getting Started

## Prerequisites

- Python ≥ 3.11
- [uv](https://docs.astral.sh/uv/) package manager
- An [OpenRouter](https://openrouter.ai/) API key

## Installation

```bash
# Clone the repo
git clone https://github.com/asvskartheek/kartheek-bs-code.git
cd kartheek-bs-code

# Install all dependencies (creates .venv automatically)
uv sync

# Create a .env file with your API key
echo "OPENROUTER_API_KEY=sk-or-..." > .env
```

## Running the agent

Phoenix **must** be running before starting the agent or evals:

```bash
bash start_phoenix.sh &
# Wait a few seconds, then:
uv run python main.py
```

The agent will answer *"What is the weather in Tokyo?"* and log the response.
Open [http://localhost:6006](http://localhost:6006) to view the trace.

## Running evaluations

```bash
uv run python eval.py --dataset dev-time-data
```

This will:

1. Create (or reuse) the `dev-time-data` dataset in Phoenix.
2. Run the agent against each example at concurrency 4.
3. Score outputs with `tool-call-correctness` and `no-followup-in-response`.
4. Print a link to the experiment results in Phoenix.

## Adding a new eval suite

Edit `eval.py` and append an entry to `EVAL_SUITES`:

```python
EVAL_SUITES["my-suite"] = EvalSuite(
    dataset_name="my-suite",
    examples=[
        {"question": "Weather in Berlin?", "expected_city": "Berlin"},
    ],
    input_keys=["question"],
    output_keys=["expected_city"],
    evaluators=lambda api_key: [tool_call_correctness],
)
```

Then run: `uv run python eval.py --dataset my-suite`
