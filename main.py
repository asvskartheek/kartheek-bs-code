"""Entry point for the kartheek-bs-code weather agent demo.

This script performs three things before running any agent logic:

1. **Phoenix health-check** — exits early with a helpful error message if the
   Phoenix observability server is not reachable at ``http://localhost:6006``.
   Start Phoenix with ``bash start_phoenix.sh &`` before running this script.

2. **OpenTelemetry instrumentation** — registers a Phoenix tracer provider and
   instruments all LangChain calls via
   :class:`~openinference.instrumentation.langchain.LangChainInstrumentor`.
   Every LLM call and tool invocation will appear as a span in the Phoenix UI.

3. **Agent invocation** — creates the travel-assistant agent and sends a sample
   weather query, logging the AI response to stdout.

Usage::

    uv run python main.py

Environment variables:
    OPENROUTER_API_KEY: Required.  Your OpenRouter API key (``sk-or-...``).
"""

import logging
import os
import sys
import urllib.request
import urllib.error

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

from dotenv import load_dotenv

load_dotenv()

from rich.console import Console

_console = Console(stderr=True)

# --- Phoenix startup check ---
try:
    urllib.request.urlopen("http://localhost:6006/healthz", timeout=2)
except (urllib.error.URLError, OSError):
    _console.print(
        "\n[bold red]ERROR: Phoenix observability server is not running![/bold red]\n"
        "[red]Start it first:[/red] [yellow]uv run bash start_phoenix.sh &[/yellow]\n"
        "[red]Then wait a few seconds and re-run this script.[/red]\n",
        highlight=False,
    )
    sys.exit(1)

from phoenix.otel import register
from openinference.instrumentation.langchain import LangChainInstrumentor

tracer_provider = register(
    project_name="kartheek-bs-code",
    endpoint="http://localhost:6006/v1/traces",
)
LangChainInstrumentor().instrument(tracer_provider=tracer_provider)

from agent import make_agent


def main() -> None:
    """Run a single weather query through the travel-assistant agent.

    Reads ``OPENROUTER_API_KEY`` from the environment (or ``.env``), creates
    an agent via :func:`~agent.make_agent`, invokes it with a hardcoded Tokyo
    weather question, and logs the final AI response.

    The function exits with code ``1`` if the API key is missing.

    Raises:
        SystemExit: With exit code ``1`` when ``OPENROUTER_API_KEY`` is unset.
    """
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        _console.print(
            "\n[bold red]ERROR: OPENROUTER_API_KEY is not set.[/bold red]\n"
            "[red]Add it to a .env file or export it in your shell:[/red]\n"
            "[yellow]  export OPENROUTER_API_KEY=sk-or-...[/yellow]\n",
            highlight=False,
        )
        sys.exit(1)

    agent = make_agent(api_key)

    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "What is the weather in Tokyo?",
                }
            ]
        }
    )

    for message in result["messages"]:
        if hasattr(message, "content") and message.__class__.__name__ == "AIMessage":
            logging.info(message.content)


if __name__ == "__main__":
    main()
