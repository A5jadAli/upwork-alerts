"""Minimal raw-HTTP MCP client for Upwork's hosted server.

We talk the Streamable-HTTP MCP protocol directly with httpx instead of using
the `mcp` SDK: the 2.x SDK mis-parses Upwork's responses and the 1.x SDK sends
an initialize the gateway rejects. Raw HTTP is simple here and immune to SDK
churn. Tools are namespaced on the server as `upwork__<name>`.
"""
import json

import httpx

import config

PROTOCOL_VERSION = "2025-06-18"
FIND_JOBS_TOOL = "upwork__find_jobs"


class UpworkMCP:
    def __init__(self, access_token: str):
        self._token = access_token
        self._sid: str | None = None
        self._http = httpx.Client(timeout=60)

    def _headers(self) -> dict:
        h = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "MCP-Protocol-Version": PROTOCOL_VERSION,
        }
        if self._sid:
            h["Mcp-Session-Id"] = self._sid
        return h

    def _post(self, payload: dict) -> httpx.Response:
        return self._http.post(config.MCP_URL, headers=self._headers(), json=payload)

    @staticmethod
    def _parse(resp: httpx.Response) -> dict:
        body = resp.text
        if "text/event-stream" in (resp.headers.get("content-type") or ""):
            body = "".join(
                line[5:].strip()
                for line in body.splitlines()
                if line.startswith("data:")
            )
        return json.loads(body)

    def initialize(self) -> None:
        r = self._post({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "upwork-alerts", "version": "1.0"},
            },
        })
        r.raise_for_status()
        self._sid = r.headers.get("mcp-session-id")
        # fire-and-forget the initialized notification (server returns 202)
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def call_tool(self, name: str, arguments: dict) -> dict:
        r = self._post({
            "jsonrpc": "2.0", "id": 2, "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        })
        if r.status_code != 200:
            raise RuntimeError(f"{name} HTTP {r.status_code}: {r.text[:300]}")
        data = self._parse(r)
        if "error" in data:
            raise RuntimeError(f"{name} error: {data['error']}")
        content = data.get("result", {}).get("content", [])
        text = "".join(c.get("text", "") for c in content if c.get("type") == "text")
        return json.loads(text)

    def find_jobs(self, query: str, filters: dict) -> list[dict]:
        payload = self.call_tool(FIND_JOBS_TOOL, {
            "action": "search",
            "org_uid": config.ORG_UID,
            "params": {"query": query, **filters},
        })
        return payload.get("jobs", [])

    def close(self) -> None:
        self._http.close()


def search_all(access_token: str) -> list[dict]:
    """Run every configured query in one MCP session, dedupe, return job dicts."""
    mcp = UpworkMCP(access_token)
    mcp.initialize()
    try:
        seen, jobs = set(), []
        for q in config.QUERIES:
            for job in mcp.find_jobs(q, config.SEARCH_FILTERS):
                jid = str(job.get("id"))
                if jid and jid not in seen:
                    seen.add(jid)
                    jobs.append(job)
        return jobs
    finally:
        mcp.close()
