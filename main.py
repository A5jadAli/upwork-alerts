"""One poll cycle: fetch fresh jobs, de-dupe, filter, and alert immediately."""
from __future__ import annotations

import time

import httpx

import config
import filter as jobfilter
import job_time
import mcp_upwork
import notify
import state


def poll_once() -> None:
    access_token = state.get_access_token()
    try:
        jobs = mcp_upwork.search_all(access_token)
    except httpx.HTTPStatusError as e:
        # Token rejected despite our cached expiry -> force one refresh and retry.
        if e.response is not None and e.response.status_code in (401, 403):
            print(f"[main] token rejected ({e.response.status_code}) — forcing refresh + retry")
            access_token = state.force_refresh()
            jobs = mcp_upwork.search_all(access_token)
        else:
            raise

    seen = state.load_seen()
    new = [j for j in jobs if str(j.get("id")) not in seen]

    pending = state.load_pending()
    added = 0
    for job in new:
        verdict = jobfilter.evaluate(job)
        if verdict.get("fit"):
            job["_score"] = verdict.get("score", 50)
            job["_reason"] = verdict.get("reason", "")
            job["_detected_at"] = time.time()
            pending["jobs"].append(job)
            added += 1

    # Mark every fetched job seen (matched or not) so it's never re-evaluated.
    seen.update(str(j.get("id")) for j in jobs if j.get("id"))
    state.save_seen(seen)

    # Persist before SMTP so a temporary email failure cannot lose an alert.
    pending["jobs"] = [
        job for job in pending["jobs"]
        if job_time.is_recent(job, config.MAX_JOB_AGE_HOURS)
    ]
    state.save_pending(pending)

    # Freshest first. The LLM score remains visible, but an older high score can
    # no longer delay a newer qualified job.
    ranked = sorted(pending["jobs"], key=job_time.published_timestamp, reverse=True)
    top = ranked[:config.ALERT_TOP_N]
    sent = 0
    if top:
        extra = max(0, len(ranked) - len(top))
        notify.send_digest(top, extra)
        sent = len(top)
        sent_ids = {str(job.get("id")) for job in top}
        pending["jobs"] = [
            job for job in ranked if str(job.get("id")) not in sent_ids
        ]
        pending["last_digest_at"] = time.time()

    state.save_pending(pending)

    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] realtime fetched={len(jobs)} new={len(new)} queued+={added} "
          f"pending={len(pending['jobs'])} sent={sent}")


if __name__ == "__main__":
    poll_once()
