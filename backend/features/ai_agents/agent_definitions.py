"""CrewAI Agent definitions for the multi-agent trading intelligence system."""
from crewai import Agent

from features.ai_agents.prompts.fundamental import FUNDAMENTAL_AGENT_BACKSTORY
from features.ai_agents.prompts.macro import MACRO_AGENT_BACKSTORY
from features.ai_agents.prompts.sentiment import SENTIMENT_AGENT_BACKSTORY
from features.ai_agents.prompts.synthesis import MANAGER_AGENT_BACKSTORY
from features.ai_agents.tools.fred_tool import FredTool
from features.ai_agents.tools.news_sentiment_tool import NewsSentimentTool
from features.ai_agents.tools.sec_edgar_tool import SecEdgarTool


def build_fundamental_agent(llm: str = "gpt-4o-mini") -> Agent:
    """Fundamental analysis agent: reads SEC filings and assesses company health."""
    return Agent(
        role="Senior Financial Analyst",
        goal=(
            "Perform deep fundamental analysis of {ticker} using SEC filings to assess "
            "revenue trajectory, balance sheet health, and earnings quality."
        ),
        backstory=FUNDAMENTAL_AGENT_BACKSTORY,
        tools=[SecEdgarTool()],
        llm=llm,
        verbose=False,
        allow_delegation=False,
        max_iter=3,
    )


def build_macro_agent(llm: str = "gpt-4o-mini") -> Agent:
    """Macroeconomic agent: monitors rates, inflation, and yield curve signals."""
    return Agent(
        role="Chief Economist",
        goal=(
            "Assess the current macroeconomic environment and its directional impact on {ticker}, "
            "focusing on interest rate cycle, inflation, yield curve, and market volatility."
        ),
        backstory=MACRO_AGENT_BACKSTORY,
        tools=[FredTool()],
        llm=llm,
        verbose=False,
        allow_delegation=False,
        max_iter=3,
    )


def build_sentiment_agent(llm: str = "gpt-4o-mini") -> Agent:
    """News sentiment agent: scores real-time financial news for a ticker."""
    return Agent(
        role="Sentiment Intelligence Analyst",
        goal=(
            "Score recent financial news and narrative for {ticker} from -1.0 (strongly bearish) "
            "to +1.0 (strongly bullish) with calibrated precision."
        ),
        backstory=SENTIMENT_AGENT_BACKSTORY,
        tools=[NewsSentimentTool()],
        llm=llm,
        verbose=False,
        allow_delegation=False,
        max_iter=3,
    )


def build_manager_agent(llm: str = "gpt-4o-mini") -> Agent:
    """Manager/CIO agent: synthesizes research into a structured trading signal."""
    return Agent(
        role="Chief Investment Officer",
        goal=(
            "Synthesize fundamental, macro, and sentiment research for {ticker} into a single "
            "actionable trading signal JSON with bias, conviction score, and reasoning."
        ),
        backstory=MANAGER_AGENT_BACKSTORY,
        tools=[],
        llm=llm,
        verbose=False,
        allow_delegation=False,
        max_iter=2,
    )
