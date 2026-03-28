import os
import random
import sys

from dotenv import load_dotenv

load_dotenv()

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
        print("Error: OPENROUTER_API_KEY is not set.")
        print("Add it to a .env file or export it in your shell:")
        print("  export OPENROUTER_API_KEY=sk-or-...")
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
