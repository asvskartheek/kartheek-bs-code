import os
import random
import sys
import urllib.request
import urllib.error

from dotenv import load_dotenv

load_dotenv()

from rich.console import Console

_console = Console(stderr=True)

# --- Phoenix startup check ---
try:
    urllib.request.urlopen("http://localhost:6006", timeout=2)
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

# Only instrument LangChain — it already captures OpenAI calls as child spans.
# auto_instrument=True would also activate openinference-instrumentation-openai,
# which creates duplicate orphaned ChatCompletion root traces.
tracer_provider = register(
    project_name="kartheek-bs-code",
    endpoint="http://localhost:6006/v1/traces",
)
LangChainInstrumentor().instrument(tracer_provider=tracer_provider)

from langchain_openai import ChatOpenAI

from deepagents import create_deep_agent


def get_weather(city: str) -> str:
    """Get the current weather for a given city.

    Args:
        city: The name of the city to get weather for.
    """
    condition = random.choice(
        ["Sunny", "Cloudy", "Rainy", "Foggy", "Snowy", "Windy", "Stormy"]
    )
    temperature = random.randint(-10, 40)
    return f"{condition}, {temperature}°C in {city}."


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

    llm = ChatOpenAI(
        model="openai/gpt-5-mini",
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    agent = create_deep_agent(
        model=llm,
        tools=[get_weather],
        system_prompt=(
            "You are a helpful travel assistant. "
            "Use the available tools to answer questions about weather."
        ),
    )

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
            print(message.content)


if __name__ == "__main__":
    main()
