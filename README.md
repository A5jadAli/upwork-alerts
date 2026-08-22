# Upwork Job Alerts — always-on, self-hosted

Polls Upwork for new AI / automation / Python jobs, filters for fit + legitimacy
with an LLM, and emails you the good ones. Runs on GitHub Actions (free on a
**public** repo), no Claude session required.

Same search recipe as the Claude Code session (identical `find_jobs` queries +
filters), so results are the same or better.

## Status: de-risking auth first
Upwork retired self-serve API keys, so we authenticate via the **client-id
metadata document** method (how Claude connected) — no developer portal needed.
Step 1 proves custom code can log in and pull jobs before we build the rest.

## Step 1 — one-time auth test (do this first)
1. Create an **empty public GitHub repo** and push this folder to it.
2. Your metadata URL is then:
   `https://raw.githubusercontent.com/<user>/<repo>/main/client-metadata.json`
   Edit `client-metadata.json` → set `client_uri` to your repo URL, commit/push.
3. Install deps and run the one-time login **on your machine**:
   ```bash
   pip install -r requirements.txt
   CLIENT_ID="https://raw.githubusercontent.com/<user>/<repo>/main/client-metadata.json" \
     python bootstrap.py
   ```
4. A browser opens → approve. The script prints:
   - your **UPWORK_REFRESH_TOKEN** (save it), and
   - the first jobs it pulled (proof it works).

If Step 1 prints jobs, the risky part is solved and I build the rest
(LLM filter + email + the GitHub Actions cron). If the refresh token misbehaves,
we fall back to the no-auth **RSS** source.

## Secrets (added later, in GitHub → Settings → Secrets → Actions)
| Secret | What |
|---|---|
| `UPWORK_REFRESH_TOKEN` | from Step 1 |
| `CLIENT_ID` | your metadata-document URL |
| `LLM_API_KEY` | OpenAI / Gemini / Grok key for the fit filter |
| `GMAIL_USER` / `GMAIL_APP_PASSWORD` | sender + 16-char app password |
| `ALERT_TO` | aliasjid009@gmail.com |

## Files
- `config.py` — endpoints, account, search queries + filters
- `auth.py` — OAuth (PKCE login + unattended refresh)
- `mcp_upwork.py` — MCP client → `find_jobs`
- `bootstrap.py` — Step 1 one-time login + proof
- *(coming after Step 1 passes)* `filter.py`, `notify.py`, `main.py`, `.github/workflows/poll.yml`
