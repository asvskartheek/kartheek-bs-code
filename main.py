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


def main():
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
