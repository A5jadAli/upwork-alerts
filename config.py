"""Central config: OAuth endpoints, the Upwork account, the search recipe,
the LLM filter, email, and runtime knobs. Values come from env (with a tiny
.env loader so local runs are easy); the always-on host sets real env vars.
"""
import os


def _load_dotenv(path=".env"):
    """Minimal .env loader (no dependency). KEY=VALUE lines; '#' comments."""
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except FileNotFoundError:
        pass


_load_dotenv()

# --- Upwork MCP + OAuth (discovered from mcp.upwork.com well-known metadata) ---
MCP_URL = "https://mcp.upwork.com/mcp"
MCP_RESOURCE = "https://mcp.upwork.com/mcp"  # RFC 8707 resource indicator
AUTHORIZATION_ENDPOINT = "https://www.upwork.com/ab/account-security/oauth2/authorize"
TOKEN_ENDPOINT = "https://www.upwork.com/api/v3/oauth2/token"

# CLIENT_ID is the PUBLIC URL where client-metadata.json is served (jsDelivr =
# application/json, which the client-id-metadata-document spec requires).
CLIENT_ID = os.environ.get(
    "CLIENT_ID",
    "https://cdn.jsdelivr.net/gh/A5jadAli/upwork-alerts@main/client-metadata.json",
)
REDIRECT_URI = "http://localhost:8765/callback"

# Your Upwork org (freelancer) uid, from list_accounts.
ORG_UID = os.environ.get("ORG_UID", "1946584904081162560")

# --- Search recipe (verbatim port of the Claude session poller) ---
QUERIES = [
    "n8n Make.com automation workflow AI",
    "AI agent RAG chatbot LLM LangChain multi-agent",
    "AI voice agent image generation fine-tuning Stable Diffusion",
    "Python FastAPI backend web scraping API developer",
]
SEARCH_FILTERS = {
    "verified_payment_only": True,
    "proposals_max": 4,          # be early: fewer than 5 proposals
    "sort": "recency",
    "limit": 10,
}
SMART_SEARCH_FILTERS = {
    "mode": "most_recent",
    "days_posted": 1,
    "verified_payment_only": True,
    "proposals_max": 4,
    "limit": 10,
}
MAX_JOB_AGE_HOURS = float(os.environ.get("MAX_JOB_AGE_HOURS", "1"))
MIN_FIXED_BUDGET = 10.0          # reject fixed-price jobs with a stated budget under $10

# --- LLM fit/legitimacy filter (OpenAI-compatible; works for OpenAI/Gemini/Grok) ---
LLM_API_KEY = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
LLM_MODEL = os.environ.get("LLM_MODEL", "gpt-5-mini")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")

# --- Email (Gmail SMTP) ---
GMAIL_USER = os.environ.get("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
ALERT_TO = os.environ.get("ALERT_TO", "aliasjid009@gmail.com")

# --- Runtime / state ---
# Poll frequently and email every qualified batch immediately. The keyword
# search action has no date filter, so freshness is also enforced client-side.
POLL_INTERVAL_SECONDS = int(os.environ.get("POLL_INTERVAL_SECONDS", "600"))
ALERT_TOP_N = int(os.environ.get("ALERT_TOP_N", "10"))

TOKEN_FILE = os.environ.get("TOKEN_FILE", "token.json")
SEEN_FILE = os.environ.get("SEEN_FILE", "seen.json")
PENDING_FILE = os.environ.get("PENDING_FILE", "pending.json")
SEEN_MAX = 800

# Freelancer profile summary the LLM uses to judge fit.
FREELANCER_PROFILE = (
    "Document AI for Search, Data Extraction & Workflows | RAG, n8n. Skills: "
    "document ingestion, data extraction, RAG search, knowledge assistants, AI "
    "agents, LangChain/LangGraph, OpenAI/LLM apps, n8n, Make.com/Zapier, API "
    "integration, Python, FastAPI, Django, web scraping, image generation, voice "
    "AI, and ML/model fine-tuning. Remote, based in Pakistan. New Upwork profile "
    "(no reviews yet), so focused early/small jobs are welcome."
)
