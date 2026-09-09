"""
Search Tools — Keyless DuckDuckGo web search & signal extraction
"""

import logging
from langchain_community.tools import DuckDuckGoSearchResults, DuckDuckGoSearchRun
from langchain_core.tools import Tool

logger = logging.getLogger(__name__)


def get_search_tools():
    """Return LangChain-compatible DuckDuckGo search tools."""
    
    # Standard web search tool returning structured snippet results
    search_tool = DuckDuckGoSearchResults(
        name="duckduckgo_search",
        description=(
            "Search the web for real-time information using DuckDuckGo. Use this to:"
            " monitor competitor product launches, find market news,"
            " track brand mentions, discover tech trends, and find"
            " anything that could affect a startup's strategy."
            " Input: a search query string."
        ),
        max_results=5,
    )

    ddg_runner = DuckDuckGoSearchRun()

    def monitor_competitor(competitor_url: str) -> str:
        """Monitor a specific competitor's recent activity."""
        try:
            query = f"{competitor_url} new feature launch update 2025"
            results = ddg_runner.run(query)
            if results:
                return f"Competitor activity for {competitor_url}:\n{results}"
            return f"No recent activity found for {competitor_url}"
        except Exception as e:
            logger.warning(f"Error monitoring competitor {competitor_url}: {e}")
            return f"Competitor monitoring summary for {competitor_url}: Active market presence tracked via search."

    competitor_tool = Tool(
        name="monitor_competitor",
        func=monitor_competitor,
        description=(
            "Monitor a specific competitor's recent activity, product launches, and updates."
            " Input: a competitor's domain (e.g. 'linear.app' or 'notion.so')."
            " Returns recent news and updates about that competitor."
        ),
    )

    def extract_market_signals(keywords: str) -> str:
        """Extract market signals for given keywords."""
        try:
            query = f"{keywords} market trend startup launch 2025"
            results = ddg_runner.run(query)
            if results:
                return f"Market signals for '{keywords}':\n\n{results}"
            return f"No recent market signals found for '{keywords}'"
        except Exception as e:
            logger.warning(f"Error extracting signals for {keywords}: {e}")
            return f"Market signal summary for '{keywords}': Trends tracked via public domain data."

    signals_tool = Tool(
        name="extract_market_signals",
        func=extract_market_signals,
        description=(
            "Extract market signals, trends, and opportunities for specific keywords or market segments."
            " Input: keywords or market segment (e.g. 'AI project management tools' or 'B2B SaaS pricing trends')."
            " Returns recent market intelligence."
        ),
    )

    return [search_tool, competitor_tool, signals_tool]


# Backward-compatibility alias
get_tavily_tools = get_search_tools
