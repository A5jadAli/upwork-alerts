"""One poll cycle.

Detection and emailing are decoupled:
  * every poll: fetch -> drop seen -> LLM filter -> queue matches in pending.json
  * every DIGEST_INTERVAL_HOURS: email the top DIGEST_TOP_N queued jobs, clear queue

So jobs are caught early and de-duped, but you get only a few high-signal emails.
"""
from __future__ import annotations

import time

import config
import filter as jobfilter
import mcp_upwork
import notify
import state


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
    due = _digest_due(pending, now)
    sent = 0
    if pending["last_digest_at"] is None:
        # First run ever: start the clock, don't email the pre-existing backlog.
        pending["last_digest_at"] = now
    elif due:
        ranked = sorted(pending["jobs"], key=lambda j: j.get("_score", 0), reverse=True)
        top = ranked[: config.DIGEST_TOP_N]
        extra = max(0, len(ranked) - len(top))
        if top:
            notify.send_digest(top, extra)
            sent = len(top)
        pending["jobs"] = []
        pending["last_digest_at"] = now

    state.save_pending(pending)

    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] fetched={len(jobs)} new={len(new)} queued+={added} "
          f"pending={len(pending['jobs'])} digest_sent={sent}")


def _digest_due(pending: dict, now: float) -> bool:
    last = pending.get("last_digest_at")
    return last is not None and (now - last) >= config.DIGEST_INTERVAL_HOURS * 3600


if __name__ == "__main__":
    poll_once()
