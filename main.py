"""One poll cycle.

Detection and emailing are decoupled:
  * every poll (30 min): fetch -> drop seen -> LLM filter+score -> queue matches
  * emailing is TIME-OF-DAY aware:
      - US peak hours  -> email at most every PEAK_GAP_MINUTES, up to PEAK_TOP_N
      - off-peak       -> email at most every OFFPEAK_GAP_HOURS, up to OFFPEAK_TOP_N
  * an email is sent ONLY when qualified matches exist — never padded, never empty.
"""
from __future__ import annotations

import time

import config
import filter as jobfilter
import mcp_upwork
import notify
import state


def _schedule(now: float):
    """Return (min_gap_seconds, cap, label) based on the current UTC hour."""
    hour = time.gmtime(now).tm_hour
    if config.PEAK_START_UTC <= hour < config.PEAK_END_UTC:
        return config.PEAK_GAP_MINUTES * 60, config.PEAK_TOP_N, "peak"
    return config.OFFPEAK_GAP_HOURS * 3600, config.OFFPEAK_TOP_N, "off-peak"


def poll_once() -> None:
    access_token = state.get_access_token()
    jobs = mcp_upwork.search_all(access_token)

    seen = state.load_seen()
    new = [j for j in jobs if str(j.get("id")) not in seen]

    pending = state.load_pending()
    added = 0
    for job in new:
        verdict = jobfilter.evaluate(job)
        if verdict.get("fit"):
            job["_score"] = verdict.get("score", 50)
            job["_reason"] = verdict.get("reason", "")
            pending["jobs"].append(job)
            added += 1

    # Mark every fetched job seen (matched or not) so it's never re-evaluated.
    seen.update(str(j.get("id")) for j in jobs if j.get("id"))
    state.save_seen(seen)

    now = time.time()
    gap, cap, label = _schedule(now)
    last = pending["last_digest_at"]
    sent = 0

    if last is None:
        # First run ever: start the clock, don't email the pre-existing backlog.
        pending["last_digest_at"] = now
    elif pending["jobs"] and (now - last) >= gap:
        # Send only what actually qualified, best-first, capped. If fewer than the
        # cap qualified, we send fewer — we never invent or pad.
        ranked = sorted(pending["jobs"], key=lambda j: j.get("_score", 0), reverse=True)
        top = ranked[:cap]
        extra = max(0, len(ranked) - len(top))
        notify.send_digest(top, extra)
        sent = len(top)
        pending["jobs"] = []
        pending["last_digest_at"] = now
    # else: due-but-empty or not-yet-due -> hold; a qualifying job goes out next window.

    state.save_pending(pending)

    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {label} fetched={len(jobs)} new={len(new)} queued+={added} "
          f"pending={len(pending['jobs'])} sent={sent}")


if __name__ == "__main__":
    poll_once()
