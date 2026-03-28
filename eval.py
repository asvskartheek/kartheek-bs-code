"""Evaluation harness for the weather agent.

This module implements a Phoenix-native evaluation pipeline that measures how
well the travel-assistant agent handles weather queries.  It uses Phoenix
*Datasets* to store labelled examples and Phoenix *Experiments* to record
task outputs and evaluator scores side-by-side.

Usage::

    uv run python eval.py [--dataset dev-time-data]

Architecture
------------
Each entry in :data:`EVAL_SUITES` is an :class:`EvalSuite` that bundles:

- A **dataset** of (question, expected_city) pairs uploaded to Phoenix.
- A **task** function (:func:`task`) that runs the agent and extracts
  structured output.
- A list of **evaluators** — one code-based (:func:`tool_call_correctness`)
  and one LLM-as-judge (:func:`make_no_followup_evaluator`) — that score each
  task output.

To add a new eval suite, append an entry to :data:`EVAL_SUITES`.

Environment variables:
    OPENROUTER_API_KEY: Required.  Your OpenRouter API key (``sk-or-...``).
"""

import argparse
import logging
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path

import yaml

_config = yaml.safe_load((Path(__file__).parent / "config.yaml").read_text())
_judge_cfg = _config["models"][_config["judge_model"]]

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
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
    logging.error("Phoenix is not running. Start it: bash start_phoenix.sh &")
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
def task(input: dict, agent) -> dict:
    """Run the agent on a single dataset example and return structured output.

    Invokes *agent* with the question from *input*, then walks the resulting
    message list to extract:

    - The first AI text response.
    - The name of the first tool that was called (if any).
    - The ``city`` argument that was passed to that tool call.

    This structured output is consumed by the evaluators so they can assert on
    tool-call correctness and response quality independently.

    Args:
        input: A dataset row dict that must contain a ``"question"`` key with
            the user's natural-language weather question.
        agent: A :func:`~agent.make_agent` DeepAgent instance.

    Returns:
        A dict with four keys:

        ``question``
            The original question string (passed through for evaluator context).
        ``tool_called``
            Name of the first tool invoked (e.g. ``"get_weather"``), or ``""``
            if no tool was called.
        ``city_arg``
            The ``city`` argument passed to the tool, or ``""`` if unavailable.
        ``response``
            The first AI text response, or ``""`` if none was produced.
    """
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
def tool_call_correctness(output: dict, expected: dict) -> EvaluationResult:
    """Score whether the agent called ``get_weather`` with the correct city.

    A code-based (deterministic) evaluator registered with Phoenix under the
    name ``"tool-call-correctness"``.  Both the tool name **and** the city
    argument must match for a passing score.

    Args:
        output: The dict returned by :func:`task`.  Must contain
            ``"tool_called"`` and ``"city_arg"`` keys.
        expected: The dataset row's expected output.  Must contain an
            ``"expected_city"`` key (case-insensitive substring match).

    Returns:
        An :class:`~phoenix.experiments.types.EvaluationResult` with:

        - ``score`` — ``1.0`` if correct, ``0.0`` otherwise.
        - ``label`` — ``"correct"`` or ``"incorrect"``.
        - ``explanation`` — a short string showing the actual vs. expected call.
    """
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


def make_no_followup_evaluator():
    """Create an LLM-as-judge evaluator that checks for follow-up questions.

    Reads judge model configuration from ``config.yaml`` (``judge_model`` key)
    and loads the API key from the environment variable named by that model's
    ``api_key_env`` field.  Returns a Phoenix evaluator that determines whether
    the agent's response directly answers the user's question or instead asks a
    follow-up / clarifying question.

    The returned evaluator is decorated with ``@create_evaluator`` and
    registered in Phoenix under the name ``"no-followup-in-response"``.

    Returns:
        A Phoenix-compatible evaluator callable that accepts a :func:`task`
        output dict and returns an :class:`~phoenix.experiments.types.EvaluationResult`
        with:

        - ``score`` — ``1.0`` for a direct answer, ``0.0`` for a follow-up.
        - ``label`` — ``"direct_answer"`` or ``"asks_follow_up"``.
        - ``explanation`` — one-sentence rationale from the judge LLM.
    """
    judge = OpenAI(
        api_key=os.environ[_judge_cfg["api_key_env"]],
        base_url=_judge_cfg["base_url"],
    )

    @create_evaluator(name="no-followup-in-response", kind="LLM")
    def no_followup_in_response(output):
        """Does the response answer directly without asking follow-up questions?"""
        resp = judge.chat.completions.create(
            model=_judge_cfg["model"],
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
    """A self-contained evaluation suite bundling a dataset with its evaluators.

    Each ``EvalSuite`` instance describes everything needed to run one
    experiment in Phoenix: the dataset name, the labelled examples, which keys
    are inputs vs. expected outputs, and a factory that returns the list of
    evaluators to apply.

    Attributes:
        dataset_name: The name under which the dataset is stored (and looked
            up) in Phoenix.  Must be unique within a Phoenix project.
        examples: A list of dicts, each representing one labelled example.
            Each dict must contain at least the keys named in *input_keys* and
            *output_keys*.
        input_keys: Column names from *examples* that Phoenix treats as the
            agent's input (e.g. ``["question"]``).
        output_keys: Column names from *examples* that Phoenix treats as the
            expected output / ground-truth (e.g. ``["expected_city"]``).
        evaluators: A callable that receives an OpenRouter API key and returns
            a list of Phoenix evaluator functions.  Using a factory (rather
            than a plain list) lets LLM-based evaluators initialise their own
            OpenAI clients lazily.
    """

    dataset_name: str
    examples: list
    input_keys: list
    output_keys: list
    # Returns evaluator list; LLM evaluators load their API keys from the environment
    evaluators: Callable[[], list] = field(repr=False)


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
        evaluators=lambda: [
            tool_call_correctness,
            make_no_followup_evaluator(),
        ],
    ),
}


# ── Main ─────────────────────────────────────────────────────────────────────
def main() -> None:
    """CLI entry point for running an evaluation suite against the weather agent.

    Parses ``--dataset`` from the command line, creates or reuses the
    corresponding Phoenix dataset, runs the experiment (agent + evaluators) at
    concurrency 4, and prints a link to the results in the Phoenix UI.

    Steps:

    1. Resolve the :class:`EvalSuite` for the requested dataset name.
    2. Connect to Phoenix via :class:`~phoenix.client.Client` and create the
       dataset if it does not already exist.
    3. Instantiate the agent with :func:`~agent.make_agent`.
    4. Call :func:`~phoenix.experiments.run_experiment` with the task and
       evaluator list from the suite.

    Raises:
        SystemExit: With exit code ``1`` when ``OPENROUTER_API_KEY`` is unset.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="dev-time-data", choices=list(EVAL_SUITES))
    args = parser.parse_args()

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
        logging.info(
            f"Created dataset '{suite.dataset_name}' with {len(suite.examples)} examples."
        )
    else:
        dataset = px_client.datasets.get_dataset(dataset=suite.dataset_name)
        logging.info(f"Using existing dataset '{suite.dataset_name}'.")

    agent = make_agent()

    run_experiment(
        dataset=dataset,
        task=lambda input: task(input, agent),
        evaluators=suite.evaluators(),
        experiment_name="weather-agent-eval",
        concurrency=4,
    )

    logging.info(
        f"Results: http://localhost:6006 → Datasets → {suite.dataset_name} → Experiments"
    )


if __name__ == "__main__":
    main()
