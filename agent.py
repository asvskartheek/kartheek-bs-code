"""Weather agent module.

Provides a simulated weather tool and a factory function that wires it into a
DeepAgent backed by an OpenRouter-hosted LLM.  The agent is intended to be
used both interactively (via ``main.py``) and programmatically inside the
Phoenix evaluation harness (``eval.py``).

Example::

    from agent import make_agent
    agent = make_agent(api_key="sk-or-...")
    result = agent.invoke({"messages": [{"role": "user", "content": "Weather in Paris?"}]})
"""

import random
from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent


def get_weather(city: str) -> str:
    """Return a simulated current-weather string for *city*.

    The function randomly selects a weather condition and temperature so that
    the agent has a non-trivial tool response to work with during development
    and evaluation.  It is intentionally non-deterministic — do **not** rely on
    its output for anything other than testing agent behaviour.

    Args:
        city: The name of the city whose weather is requested (e.g. ``"Tokyo"``).

    Returns:
        A human-readable string of the form ``"<Condition>, <temp>°C in <city>."``,
        e.g. ``"Sunny, 22°C in Tokyo."``.

    Example::

        >>> get_weather("London")
        'Rainy, 12°C in London.'
    """
    condition = random.choice(
        ["Sunny", "Cloudy", "Rainy", "Foggy", "Snowy", "Windy", "Stormy"]
    )
    temperature = random.randint(-10, 40)
    return f"{condition}, {temperature}°C in {city}."


def make_agent(api_key: str):
    """Create and return a travel-assistant DeepAgent with weather tool access.

    Instantiates a :class:`~langchain_openai.ChatOpenAI` model pointed at the
    OpenRouter gateway, then wraps it in a ``DeepAgent`` that has access to
    :func:`get_weather`.  The system prompt instructs the agent to answer
    weather-related travel questions using the tool rather than hallucinating.

    Args:
        api_key: A valid OpenRouter API key (``sk-or-...``).  Passed directly
            to the underlying LLM client; never logged or stored.

    Returns:
        A ``DeepAgent`` instance ready to be invoked with a LangChain-style
        messages dict, e.g.::

            agent.invoke({"messages": [{"role": "user", "content": "..."}]})

    Raises:
        :class:`~langchain_openai.AuthenticationError`: If *api_key* is invalid
            and the first LLM call is attempted.
    """
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
