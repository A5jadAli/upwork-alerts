"""Central config: OAuth endpoints, the Upwork account, and the search recipe.

The search queries + filters below are a verbatim port of what ran in the
Claude Code session, so results are the same (or better, since we can enrich).
"""

# --- Upwork MCP + OAuth (discovered from mcp.upwork.com well-known metadata) ---
MCP_URL = "https://mcp.upwork.com/mcp"
MCP_RESOURCE = "https://mcp.upwork.com/mcp"  # RFC 8707 resource indicator
AUTHORIZATION_ENDPOINT = "https://www.upwork.com/ab/account-security/oauth2/authorize"
TOKEN_ENDPOINT = "https://www.upwork.com/api/v3/oauth2/token"

# CLIENT_ID is the PUBLIC URL where client-metadata.json is served.
# After you push this repo public, set it to e.g.:
#   https://raw.githubusercontent.com/<user>/<repo>/main/client-metadata.json
# (or override with the CLIENT_ID env var).
import os
CLIENT_ID = os.environ.get(
    "CLIENT_ID",
    "https://raw.githubusercontent.com/A5jadAli/upwork-alerts/main/client-metadata.json",
)

REDIRECT_URI = "http://localhost:8765/callback"

# Your Upwork org (freelancer) uid, from list_accounts.
ORG_UID = os.environ.get("ORG_UID", "1946584904081162560")

# --- Search recipe (ported from the session poller) ---
QUERIES = [
    "n8n Make.com automation workflow AI",
    "AI agent RAG chatbot LLM LangChain multi-agent",
    "AI voice agent image generation fine-tuning Stable Diffusion",
    "Python FastAPI backend web scraping API developer",
]

# Server-side filters applied to every query.
SEARCH_FILTERS = {
    "verified_payment_only": True,
    "proposals_max": 4,          # be early: fewer than 5 proposals
    "sort": "recency",
    "limit": 10,
}

MIN_FIXED_BUDGET = 10.0          # reject fixed-price jobs under $10
