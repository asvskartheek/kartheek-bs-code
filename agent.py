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

import os
import random
from pathlib import Path

import yaml
from langchain_openai import ChatOpenAI
from deepagents import create_deep_agent

_config = yaml.safe_load((Path(__file__).parent / "config.yaml").read_text())
_agent_cfg = _config["models"][_config["agent_model"]]


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


def make_agent():
    """Create and return a travel-assistant DeepAgent with weather tool access.

    Reads model configuration from ``config.yaml`` (``agent_model`` key) and
    loads the API key from the environment variable named by that model's
    ``api_key_env`` field.  Instantiates a
    :class:`~langchain_openai.ChatOpenAI` model pointed at the configured
    gateway, then wraps it in a ``DeepAgent`` that has access to
    :func:`get_weather`.

    Returns:
        A ``DeepAgent`` instance ready to be invoked with a LangChain-style
        messages dict, e.g.::

            agent.invoke({"messages": [{"role": "user", "content": "..."}]})

    Raises:
        KeyError: If the environment variable named by ``api_key_env`` is unset.
        :class:`~langchain_openai.AuthenticationError`: If the API key is
            invalid and the first LLM call is attempted.
    """
    llm = ChatOpenAI(
        model=_agent_cfg["model"],
        base_url=_agent_cfg["base_url"],
        api_key=os.environ[_agent_cfg["api_key_env"]],
    )
    return create_deep_agent(
        model=llm,
        tools=[get_weather],
        system_prompt=(
            "You are a helpful travel assistant. "
            "Use the available tools to answer questions about weather."
        ),
    )
