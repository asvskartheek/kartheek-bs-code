"""
Evals for the weather agent.

Usage:  uv run python eval.py [--dataset dev-time-data]

Each entry in EVAL_SUITES defines a dataset + its evaluators together.
To add a new eval suite, add an entry to EVAL_SUITES.
"""

import argparse
import os
import sys
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Callable

import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ── Phoenix startup check ────────────────────────────────────────────────────
try:
    urllib.request.urlopen("http://localhost:6006/healthz", timeout=2)
except (urllib.error.URLError, OSError):
    print("ERROR: Phoenix is not running. Start it: bash start_phoenix.sh &")
    sys.exit(1)

from phoenix.otel import register
from openinference.instrumentation.langchain import LangChainInstrumentor
from phoenix.client import Client
from phoenix.experiments import run_experiment
from phoenix.experiments.evaluators import create_evaluator
from phoenix.experiments.types import EvaluationResult

from agent import make_agent

tracer_provider = register(
    project_name="kartheek-bs-code",
    endpoint="http://localhost:6006/v1/traces",
)
LangChainInstrumentor().instrument(tracer_provider=tracer_provider)


# ── Task: runs the agent, returns structured output for evaluators ────────────
def task(input, agent):
    result = agent.invoke(
        {"messages": [{"role": "user", "content": input["question"]}]}
    )

    tool_called, city_arg, response = "", "", ""
    for msg in result["messages"]:
        if msg.__class__.__name__ == "AIMessage":
            if not response:
                response = msg.content or ""
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                tc = msg.tool_calls[0]
                tool_called = tc.get("name", "")
                city_arg = tc.get("args", {}).get("city", "")

    return {
        "question": input["question"],
        "tool_called": tool_called,
        "city_arg": city_arg,
        "response": response,
    }


# ── Evaluators ────────────────────────────────────────────────────────────────
@create_evaluator(name="tool-call-correctness", kind="CODE")
def tool_call_correctness(output, expected):
    """Did the agent call get_weather with the correct city?"""
    correct_tool = output.get("tool_called") == "get_weather"
    expected_city = expected.get("expected_city", "")
    correct_city = expected_city.lower() in output.get("city_arg", "").lower()
    passed = correct_tool and correct_city
    return EvaluationResult(
        score=1.0 if passed else 0.0,
        label="correct" if passed else "incorrect",
        explanation=f"called={output.get('tool_called')!r}({output.get('city_arg')!r}), expected get_weather({expected_city!r})",
    )


JUDGE_PROMPT = """\
Does this AI response directly answer the user's question WITHOUT asking any
follow-up questions or requesting clarification?

Question: {question}
Response: {response}

Reply with exactly one word on the first line: direct_answer or asks_follow_up.
Then briefly explain why (1 sentence).
"""


def make_no_followup_evaluator(api_key: str):
    judge = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")

    @create_evaluator(name="no-followup-in-response", kind="LLM")
    def no_followup_in_response(output):
        """Does the response answer directly without asking follow-up questions?"""
        resp = judge.chat.completions.create(
            model="openai/gpt-4o-mini",
            temperature=0.0,
            messages=[
                {
                    "role": "user",
                    "content": JUDGE_PROMPT.format(
                        question=output.get("question", ""),
                        response=output.get("response", ""),
                    ),
                }
            ],
        )
        raw = resp.choices[0].message.content.strip()
        lines = raw.split("\n", 1)
        label = (
            "direct_answer" if "direct_answer" in lines[0].lower() else "asks_follow_up"
        )
        return EvaluationResult(
            score=1.0 if label == "direct_answer" else 0.0,
            label=label,
            explanation=lines[1].strip() if len(lines) > 1 else "",
        )

    return no_followup_in_response


# ── Eval suites: dataset + evaluators defined together ────────────────────────
@dataclass
class EvalSuite:
    dataset_name: str
    examples: list
    input_keys: list
    output_keys: list
    # Returns evaluator list; receives api_key so LLM evaluators can init their clients
    evaluators: Callable[[str], list] = field(repr=False)


EVAL_SUITES: dict[str, EvalSuite] = {
    "dev-time-data": EvalSuite(
        dataset_name="dev-time-data",
        examples=[
            {"question": "What is the weather in Tokyo?", "expected_city": "Tokyo"},
            {"question": "What is the weather in Sydney?", "expected_city": "Sydney"},
            {
                "question": "What is the weather in Hyderabad?",
                "expected_city": "Hyderabad",
            },
        ],
        input_keys=["question"],
        output_keys=["expected_city"],
        evaluators=lambda api_key: [
            tool_call_correctness,
            make_no_followup_evaluator(api_key),
        ],
    ),
}


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="dev-time-data", choices=list(EVAL_SUITES))
    args = parser.parse_args()

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not set.")
        sys.exit(1)

    suite = EVAL_SUITES[args.dataset]
    px_client = Client()

    existing = {ds["name"] for ds in px_client.datasets.list()}
    if suite.dataset_name not in existing:
        dataset = px_client.datasets.create_dataset(
            name=suite.dataset_name,
            dataframe=pd.DataFrame(suite.examples),
            input_keys=suite.input_keys,
            output_keys=suite.output_keys,
        )
        print(
            f"Created dataset '{suite.dataset_name}' with {len(suite.examples)} examples."
        )
    else:
        dataset = px_client.datasets.get_dataset(dataset=suite.dataset_name)
        print(f"Using existing dataset '{suite.dataset_name}'.")

    agent = make_agent(api_key)

    run_experiment(
        dataset=dataset,
        task=lambda input: task(input, agent),
        evaluators=suite.evaluators(api_key),
        experiment_name="weather-agent-eval",
        concurrency=1,
    )

    print(
        f"\nResults: http://localhost:6006 → Datasets → {suite.dataset_name} → Experiments"
    )


if __name__ == "__main__":
    main()
