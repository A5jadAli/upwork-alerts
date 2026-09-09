"""Minimal raw-HTTP MCP client for Upwork's hosted server.

We talk the Streamable-HTTP MCP protocol directly with httpx instead of using
the `mcp` SDK: the 2.x SDK mis-parses Upwork's responses and the 1.x SDK sends
an initialize the gateway rejects. Raw HTTP is simple here and immune to SDK
churn. Tools are namespaced on the server as `upwork__<name>`.
"""
from __future__ import annotations

import json

import httpx

import config
import job_time

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

    def smart_search(self, filters: dict) -> list[dict]:
        """Read Upwork's personalized Most Recent recommendation feed."""
        payload = self.call_tool(FIND_JOBS_TOOL, {
            "action": "smart_search",
            "org_uid": config.ORG_UID,
            "params": filters,
        })
        return payload.get("jobs", [])

    def close(self) -> None:
        self._http.close()


def search_all(access_token: str) -> list[dict]:
    """Combine personalized and keyword results, then enforce true freshness."""
    mcp = UpworkMCP(access_token)
    mcp.initialize()
    try:
        result_sets = [mcp.smart_search(config.SMART_SEARCH_FILTERS)]
        for q in config.QUERIES:
            result_sets.append(mcp.find_jobs(q, config.SEARCH_FILTERS))

        seen, jobs = set(), []
        raw_count = 0
        old_count = 0
        undated_count = 0
        applied_count = 0
        for results in result_sets:
            for job in results:
                raw_count += 1
                raw_id = job.get("id") or job.get("job_id")
                if not raw_id:
                    continue
                jid = str(raw_id)
                if jid in seen:
                    continue
                seen.add(jid)
                job["id"] = jid
                if job.get("applied") is True or job.get("is_applied") is True:
                    applied_count += 1
                    continue
                if job_time.published_at(job) is None:
                    undated_count += 1
                    continue
                if not job_time.is_recent(job, config.MAX_JOB_AGE_MINUTES):
                    old_count += 1
                    continue
                jobs.append(job)

        jobs.sort(key=job_time.published_timestamp, reverse=True)
        print(
            f"[mcp] raw={raw_count} unique={len(seen)} fresh={len(jobs)} "
            f"old={old_count} undated={undated_count} applied={applied_count}"
        )
        return jobs
    finally:
        mcp.close()
