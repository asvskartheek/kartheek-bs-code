import random
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


def make_agent(api_key: str):
    llm = ChatOpenAI(
        model="openai/gpt-4o-mini",
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    return create_deep_agent(
        model=llm,
        tools=[get_weather],
        system_prompt=(
            "You are a helpful travel assistant. "
            "Use the available tools to answer questions about weather."
        ),
    )
