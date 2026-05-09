"""CrewAI Task definitions for each agent in the trading intelligence system."""
from crewai import Agent, Task

from features.ai_agents.prompts.fundamental import (
    FUNDAMENTAL_TASK_DESCRIPTION,
    FUNDAMENTAL_TASK_EXPECTED_OUTPUT,
)
from features.ai_agents.prompts.macro import (
    MACRO_TASK_DESCRIPTION,
    MACRO_TASK_EXPECTED_OUTPUT,
)
from features.ai_agents.prompts.sentiment import (
    SENTIMENT_TASK_DESCRIPTION,
    SENTIMENT_TASK_EXPECTED_OUTPUT,
)
from features.ai_agents.prompts.synthesis import (
    MANAGER_TASK_DESCRIPTION,
    MANAGER_TASK_EXPECTED_OUTPUT,
)


def build_fundamental_task(agent: Agent, ticker: str) -> Task:
    """Task for the fundamental analyst: analyze SEC filings."""
    return Task(
        description=FUNDAMENTAL_TASK_DESCRIPTION.format(ticker=ticker),
        expected_output=FUNDAMENTAL_TASK_EXPECTED_OUTPUT.format(ticker=ticker),
        agent=agent,
    )


def build_macro_task(agent: Agent, ticker: str) -> Task:
    """Task for the macro economist: assess the rate/inflation environment."""
    return Task(
        description=MACRO_TASK_DESCRIPTION.format(ticker=ticker),
        expected_output=MACRO_TASK_EXPECTED_OUTPUT.format(ticker=ticker),
        agent=agent,
    )


def build_sentiment_task(agent: Agent, ticker: str) -> Task:
    """Task for the sentiment analyst: score recent news headlines."""
    return Task(
        description=SENTIMENT_TASK_DESCRIPTION.format(ticker=ticker),
        expected_output=SENTIMENT_TASK_EXPECTED_OUTPUT.format(ticker=ticker),
        agent=agent,
    )


def build_synthesis_task(
    manager_agent: Agent,
    ticker: str,
    context_tasks: list[Task],
) -> Task:
    """Manager synthesis task: consumes sub-agent reports and produces the final signal JSON."""
    return Task(
        description=MANAGER_TASK_DESCRIPTION.format(ticker=ticker),
        expected_output=MANAGER_TASK_EXPECTED_OUTPUT,
        agent=manager_agent,
        context=context_tasks,
    )
