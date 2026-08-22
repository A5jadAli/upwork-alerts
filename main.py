"""One poll cycle: get token -> search -> drop seen -> filter -> email -> save seen."""
import time

import config
import filter as jobfilter
import mcp_upwork
import notify
import state


def poll_once() -> list[dict]:
    access_token = state.get_access_token()
    jobs = mcp_upwork.search_all(access_token)

    seen = state.load_seen()
    new = [j for j in jobs if str(j.get("id")) not in seen]

    matched = []
    for job in new:
        verdict = jobfilter.evaluate(job)
        if verdict.get("fit"):
            job["_reason"] = verdict.get("reason", "")
            matched.append(job)

    notify.send_jobs(matched)

    # Mark every fetched job seen (both matched and rejected) so we never
    # re-evaluate the same post — same behavior as the Claude session.
    seen.update(str(j.get("id")) for j in jobs if j.get("id"))
    state.save_seen(seen)

    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] fetched={len(jobs)} new={len(new)} matched={len(matched)}")
    return matched


if __name__ == "__main__":
    poll_once()
