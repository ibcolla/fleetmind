"""
Composio Tools — 250+ integrations for taking action
Covers: GitHub, Slack, Notion, Gmail, Linear, and more
"""

import os
import logging
from langchain_core.tools import Tool

logger = logging.getLogger(__name__)


def get_composio_tools():
    """Return LangChain-compatible Composio action tools."""
    try:
        from composio_langchain import ComposioToolSet, App, Action

        toolset = ComposioToolSet(api_key=os.getenv("COMPOSIO_API_KEY"))

        # Core actions FleetMind uses most
        tools = toolset.get_tools(actions=[
            # GitHub
            Action.GITHUB_CREATE_AN_ISSUE,
            Action.GITHUB_CREATES_A_NEW_COMMENT,
            # Slack
            Action.SLACK_SENDS_A_MESSAGE_TO_A_SLACK_CHANNEL,
            # Notion
            Action.NOTION_CREATE_PAGE,
            # Gmail
            Action.GMAIL_CREATE_EMAIL_DRAFT,
            # Linear (project management)
            Action.LINEAR_CREATE_ISSUE,
        ])

        logger.info(f"Loaded {len(tools)} Composio tools")
        return tools

    except ImportError:
        logger.warning("composio_langchain not installed, using mock tools")
        return _get_mock_composio_tools()
    except Exception as e:
        logger.warning(f"Composio setup failed ({e}), using mock tools")
        return _get_mock_composio_tools()


def _get_mock_composio_tools():
    """Mock tools for development/demo without Composio credentials."""

    def create_github_issue(input_str: str) -> str:
        logger.info(f"[MOCK] Creating GitHub issue: {input_str}")
        return f"✅ [MOCK] GitHub issue created: '{input_str[:100]}' — Issue #42 (https://github.com/yourrepo/fleetmind/issues/42)"

    def send_slack_message(input_str: str) -> str:
        logger.info(f"[MOCK] Sending Slack message: {input_str}")
        return f"✅ [MOCK] Slack message sent to #general: '{input_str[:100]}'"

    def create_notion_page(input_str: str) -> str:
        logger.info(f"[MOCK] Creating Notion page: {input_str}")
        return f"✅ [MOCK] Notion page created: '{input_str[:100]}' — https://notion.so/fleetmind/page-abc123"

    def draft_email(input_str: str) -> str:
        logger.info(f"[MOCK] Drafting email: {input_str}")
        return f"✅ [MOCK] Email draft created in Gmail: '{input_str[:100]}'"

    def create_linear_issue(input_str: str) -> str:
        logger.info(f"[MOCK] Creating Linear issue: {input_str}")
        return f"✅ [MOCK] Linear issue created: '{input_str[:100]}' — LIN-101"

    return [
        Tool(
            name="create_github_issue",
            func=create_github_issue,
            description=(
                "Create a GitHub issue in the founder's repository."
                " Use when you discover a competitor feature gap, a bug to track, or a task to create."
                " Input: JSON with 'title', 'body', 'labels' fields."
            ),
        ),
        Tool(
            name="send_slack_message",
            func=send_slack_message,
            description=(
                "Send a message to a Slack channel."
                " Use for urgent signals, team alerts, or sharing intelligence."
                " Input: JSON with 'channel' and 'message' fields."
            ),
        ),
        Tool(
            name="create_notion_page",
            func=create_notion_page,
            description=(
                "Create a Notion page with structured content."
                " Use for competitor analysis reports, market research summaries, or strategic documents."
                " Input: JSON with 'title' and 'content' fields."
            ),
        ),
        Tool(
            name="draft_email",
            func=draft_email,
            description=(
                "Draft an email in Gmail without sending it."
                " Use for outreach, investor updates, or partnership emails triggered by signals."
                " Input: JSON with 'to', 'subject', 'body' fields."
            ),
        ),
        Tool(
            name="create_linear_issue",
            func=create_linear_issue,
            description=(
                "Create a Linear issue for project/product management."
                " Use when a signal requires a product response or engineering task."
                " Input: JSON with 'title', 'description', 'priority' fields."
            ),
        ),
    ]
