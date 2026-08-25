"""Persistent state on the host's local disk: the OAuth token (with rotation)
and the set of already-seen job ids.

Upwork rotates the refresh token on every refresh and the old one becomes
invalid immediately, so we ALWAYS persist the new pair. The access token lasts
~24h, so we only refresh when it's within 1h of expiry — roughly once a day.
"""
import json
import time

import auth
import config


def _load(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def load_tokens() -> dict:
    return _load(config.TOKEN_FILE, {})


def save_tokens(t: dict) -> None:
    with open(config.TOKEN_FILE, "w") as f:
        json.dump(t, f, indent=2)


def get_access_token() -> str:
    t = load_tokens()
    if not t.get("refresh_token") and not t.get("access_token"):
        raise SystemExit(
            f"No usable {config.TOKEN_FILE}. Run `python bootstrap.py` once to log in."
        )
    now = time.time()
    if t.get("access_token") and now < t.get("expires_at", 0) - 3600:
        return t["access_token"]

    # Refresh (rotates the refresh token — persist the new pair immediately).
    resp = auth.refresh(t["refresh_token"])
    t["access_token"] = resp["access_token"]
    if resp.get("refresh_token"):
        t["refresh_token"] = resp["refresh_token"]
    t["expires_at"] = now + int(resp.get("expires_in", 86400))
    save_tokens(t)
    hrs = int(resp.get("expires_in", 0)) / 3600
    print(f"[state] refreshed access token; valid ~{hrs:.0f}h")
    return t["access_token"]


def force_refresh() -> str:
    """Refresh regardless of the cached expiry (used to self-heal after a 401)."""
    t = load_tokens()
    resp = auth.refresh(t["refresh_token"])
    t["access_token"] = resp["access_token"]
    if resp.get("refresh_token"):
        t["refresh_token"] = resp["refresh_token"]
    t["expires_at"] = time.time() + int(resp.get("expires_in", 86400))
    save_tokens(t)
    print("[state] force-refreshed access token after a 401")
    return t["access_token"]


def load_seen() -> set:
    return set(_load(config.SEEN_FILE, {"seen_ids": []}).get("seen_ids", []))


def save_seen(ids) -> None:
    ids = list(ids)[-config.SEEN_MAX:]
    with open(config.SEEN_FILE, "w") as f:
        json.dump({"seen_ids": ids}, f)


# --- Pending digest queue ---
# pending.json = {"last_digest_at": <epoch or null>, "jobs": [ <job + _score/_reason> ]}

def load_pending() -> dict:
    p = _load(config.PENDING_FILE, {"last_digest_at": None, "jobs": []})
    p.setdefault("last_digest_at", None)
    p.setdefault("jobs", [])
    return p


def save_pending(p: dict) -> None:
    with open(config.PENDING_FILE, "w") as f:
        json.dump(p, f)
