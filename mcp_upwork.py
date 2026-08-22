"""Thin MCP client for Upwork's hosted server. Calls the same `find_jobs` tool
the Claude session used, with the same {action, org_uid, params} shape.
"""
import asyncio
import json

from mcp import ClientSession
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client

import config


async def _call_find_jobs(access_token: str, query: str, filters: dict) -> list[dict]:
    headers = {"Authorization": f"Bearer {access_token}"}
    async with create_mcp_http_client(headers=headers) as http_client:
        async with streamable_http_client(config.MCP_URL, http_client=http_client) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "find_jobs",
                    {
                        "action": "search",
                        "org_uid": config.ORG_UID,
                        "params": {"query": query, **filters},
                    },
                )
    text = "".join(
        c.text for c in result.content if getattr(c, "type", None) == "text"
    )
    data = json.loads(text)
    return data.get("jobs", [])


def search_all(access_token: str) -> list[dict]:
    """Run every configured query, dedupe within this poll, return job dicts."""
    async def _run():
        seen, jobs = set(), []
        for q in config.QUERIES:
            for job in await _call_find_jobs(access_token, q, config.SEARCH_FILTERS):
                jid = str(job.get("id"))
                if jid not in seen:
                    seen.add(jid)
                    jobs.append(job)
        return jobs

    return asyncio.run(_run())
