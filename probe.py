"""Diagnostic: use the saved access token to list tools + surface the real
find_jobs error (code/message/data), which the MCPError otherwise hides.
"""
import asyncio
import json

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

import config


async def main():
    tok = json.load(open("token.json"))["access_token"]
    headers = {"Authorization": f"Bearer {tok}"}
    async with streamablehttp_client(config.MCP_URL, headers=headers) as (r, w, _):
            async with ClientSession(r, w) as s:
                await s.initialize()
                # (skip list_tools: SDK rejects Upwork's cacheScope:'' — not needed)

                # Try the call and dump the true error.
                try:
                    res = await s.call_tool(
                        "find_jobs",
                        {"action": "search", "org_uid": config.ORG_UID,
                         "params": {"query": "n8n", "limit": 3}},
                    )
                    print("\nRESULT OK. content types:",
                          [getattr(c, "type", "?") for c in res.content])
                    for c in res.content:
                        if getattr(c, "type", None) == "text":
                            print(c.text[:600])
                except Exception as e:
                    print("\nERROR type:", type(e).__name__)
                    for attr in ("code", "message", "data"):
                        print(f"  {attr}:", getattr(e, attr, None))
                    print("  repr:", repr(e)[:500])


if __name__ == "__main__":
    asyncio.run(main())
