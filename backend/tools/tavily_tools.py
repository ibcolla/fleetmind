"""
Tavily Tools — Real-time web search & signal extraction
"""

import os
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.tools import Tool
from tavily import TavilyClient


def get_tavily_tools():
    """Return LangChain-compatible Tavily tools."""
    api_key = os.getenv("TAVILY_API_KEY")

    # Standard search tool
    search_tool = TavilySearchResults(
        api_key=api_key,
        max_results=5,
        search_depth="advanced",
        include_answer=True,
        include_raw_content=False,
        name="tavily_search",
        description=(
            "Search the web for real-time information. Use this to:"
            " monitor competitor product launches, find market news,"
            " track brand mentions, discover tech trends, and find"
            " anything that could affect a startup's strategy."
            " Input: a search query string."
        ),
    )

    # Competitor monitoring tool
    client = TavilyClient(api_key=api_key)

    def monitor_competitor(competitor_url: str) -> str:
        """Monitor a specific competitor's recent activity."""
        try:
            results = client.search(
                query=f"site:{competitor_url} OR \"{competitor_url}\" new feature launch update 2025",
                search_depth="advanced",
                max_results=5,
                include_answer=True,
            )
            if results.get("answer"):
                return f"Competitor activity for {competitor_url}:\n{results['answer']}\n\nSources: " + \
                       ", ".join([r.get("url", "") for r in results.get("results", [])])
            return f"No recent activity found for {competitor_url}"
        except Exception as e:
            return f"Error monitoring competitor: {str(e)}"

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
            results = client.search(
                query=f"{keywords} market trend startup launch funding 2025",
                search_depth="advanced",
                max_results=7,
                include_answer=True,
            )
            signals = []
            for r in results.get("results", []):
                signals.append(f"• {r.get('title', '')}: {r.get('content', '')[:200]}...")
            answer = results.get("answer", "")
            return f"Market signals for '{keywords}':\n\n{answer}\n\nDetailed results:\n" + "\n".join(signals)
        except Exception as e:
            return f"Error extracting signals: {str(e)}"

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
