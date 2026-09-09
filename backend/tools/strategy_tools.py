"""
FleetMind — Cloud Strategy Brief Artifact Generator Tool
---------------------------------------------------------
Generates Markdown strategy briefs and uploads them directly to Supabase Storage
in the tenant-isolated 'artifacts' bucket under path `{workspace_id}/{filename}.md`.
Eliminates local filesystem export dependencies.
"""

import uuid
import logging
from typing import Optional, Any
from langchain_core.tools import Tool

logger = logging.getLogger(__name__)


async def save_strategy_brief_to_storage(
    title: str,
    content: str,
    workspace_id: str,
    db: Any,
) -> str:
    """
    Save a generated strategy brief directly to Supabase Storage.

    Args:
        title: Brief title.
        content: Strategy Markdown text.
        workspace_id: Verified workspace UUID (derived from JWT).
        db: Supabase async client instance.

    Returns:
        Formatted result with secure cloud storage download link.
    """
    try:
        slug = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in title).lower().strip("_")
        filename = f"{slug or 'strategy_brief'}_{uuid.uuid4().hex[:8]}.md"
        storage_path = f"{workspace_id}/{filename}"
        file_bytes = content.encode("utf-8")

        # Upload file bytes to 'artifacts' bucket
        await db.storage.from_("artifacts").upload(
            path=storage_path,
            file=file_bytes,
            file_options={"content-type": "text/markdown; charset=utf-8"},
        )

        # Generate signed URL valid for 1 hour (3600 seconds)
        signed_res = await db.storage.from_("artifacts").create_signed_url(
            path=storage_path,
            expires_in=3600,
        )

        signed_url = ""
        if isinstance(signed_res, dict):
            signed_url = signed_res.get("signedURL") or signed_res.get("signedUrl") or ""
        elif hasattr(signed_res, "signed_url"):
            signed_url = signed_res.signed_url
        elif isinstance(signed_res, str):
            signed_url = signed_res

        if not signed_url:
            pub_res = db.storage.from_("artifacts").get_public_url(storage_path)
            signed_url = pub_res if isinstance(pub_res, str) else str(pub_res)

        return (
            f"✅ Strategy Brief '{title}' generated & saved to Cloud Storage!\n"
            f"Storage Path: `artifacts/{storage_path}`\n"
            f"🔗 Download Link: {signed_url}"
        )
    except Exception as e:
        logger.error(f"Strategy brief cloud storage upload failed: {e}")
        return f"Error saving strategy brief to cloud storage: {str(e)}"
