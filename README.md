# Upwork Job Alerts — always-on, self-hosted

Polls Upwork for new AI / automation / Python jobs, filters for **fit +
legitimacy** with an LLM, and **emails a periodic digest of the best ones**.
Runs as a small always-on process — no Claude session required.

Detection and emailing are **decoupled**, and emailing is **time-of-day aware**:
it polls often (to catch jobs while they still have few proposals) and emails
**faster/smaller during US business hours** (apply early) and **slower/larger
off-peak**. An email is sent **only when qualified matches exist** — never
padded to a count, never empty.

## How it works
```
loop.py  (poll every POLL_INTERVAL_SECONDS, default 30 min)
  -> state.get_access_token()      # 24h token; refreshes ~once/day, persists rotation
  -> mcp_upwork.search_all()       # raw Streamable-HTTP MCP -> upwork__find_jobs (4 queries)
  -> drop already-seen (seen.json)
  -> filter.evaluate()             # LLM fit/legitimacy + 0-100 score + code budget gate
  -> queue matches in pending.json
  -> emailing (time-of-day aware, only if matches exist):
       US peak hours  -> notify.send_digest()  every PEAK_GAP_MINUTES,  up to PEAK_TOP_N (5)
       off-peak       -> notify.send_digest()  every OFFPEAK_GAP_HOURS, up to OFFPEAK_TOP_N (10)
```

Auth uses the **client-id metadata document** method (no Upwork developer app
needed — Upwork retired those). The client identity is `client-metadata.json`,
served as application/json via jsDelivr.

### Files
| File | Role |
|---|---|
| `config.py` | endpoints, account, queries/filters, LLM + email + runtime settings |
| `auth.py` | OAuth: PKCE login + unattended refresh |
| `bootstrap.py` | **one-time** browser login → writes `token.json` |
| `mcp_upwork.py` | raw-HTTP MCP client → `upwork__find_jobs` |
| `state.py` | token store (rotation-safe) + seen-jobs store |
| `filter.py` | LLM fit/legitimacy judgment (untrusted-data safe) |
| `notify.py` | Gmail email |
| `main.py` | one poll cycle · `loop.py` runs it forever |

---

## Setup

### 1. One-time login (creates `token.json`)
On your machine (needs a browser):
```bash
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
./.venv/bin/python bootstrap.py
```
Approve in the browser. `token.json` is written (gitignored).

### 2. Configure `.env`
```bash
cp .env.example .env    # then edit
```
- **LLM key** — OpenAI by default (`gpt-5-mini`). Swap `LLM_BASE_URL`+`LLM_MODEL`
  for Gemini or Grok (see `.env.example`). Without a key, the filter passes
  everything through (still de-duped, just unfiltered).
- **Gmail** — `GMAIL_USER` + a 16-char **App Password**
  (myaccount.google.com/apppasswords, needs 2-Step Verification on). `ALERT_TO`
  is where alerts go.

### 3. Test locally
```bash
./.venv/bin/python main.py      # one cycle; check it emails / logs matches
```

---

## Deploy (pick one)

### A. Docker (recommended — portable)
State lives on a mounted volume so `token.json`/`seen.json` survive restarts.
```bash
# seed the volume with your token.json first:
docker volume create upwork_data
docker run --rm -v upwork_data:/data -v "$PWD/token.json:/seed/token.json:ro" \
  busybox cp /seed/token.json /data/token.json

docker build -t upwork-alerts .
docker run -d --name upwork-alerts --restart unless-stopped \
  --env-file .env -v upwork_data:/data upwork-alerts
docker logs -f upwork-alerts
```

### B. VPS + systemd
```ini
# /etc/systemd/system/upwork-alerts.service
[Unit]
Description=Upwork Job Alerts
After=network-online.target

[Service]
WorkingDirectory=/opt/upwork-alerts
EnvironmentFile=/opt/upwork-alerts/.env
ExecStart=/opt/upwork-alerts/.venv/bin/python loop.py
Restart=always
RestartSec=15

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl enable --now upwork-alerts
journalctl -u upwork-alerts -f
```
(Copy your `token.json` into `/opt/upwork-alerts/` first.)

### C. Fly.io (free-ish, with a volume)
`fly launch` (no deploy), `fly volumes create upwork_data -s 1`, mount at `/data`,
set secrets with `fly secrets set`, then `fly deploy`.

---

## Token notes
- Access token lasts **24h**; `state.py` refreshes ~once/day.
- Refresh tokens are **single-use & rotate** — `state.py` persists the new pair
  every time. If the chain ever breaks (e.g. the host lost `token.json`), just
  re-run `bootstrap.py` and redeploy the new `token.json`.

## Tuning
Edit `QUERIES`, `SEARCH_FILTERS`, `MIN_FIXED_BUDGET`, or `FREELANCER_PROFILE`
in `config.py`. Cadence knobs (config or env): `POLL_INTERVAL_SECONDS` (default
1800), `PEAK_START_UTC`/`PEAK_END_UTC` (peak window), `PEAK_GAP_MINUTES` (30) +
`PEAK_TOP_N` (5), `OFFPEAK_GAP_HOURS` (3) + `OFFPEAK_TOP_N` (10).
