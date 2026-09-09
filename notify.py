"""Email the matched jobs via Gmail SMTP."""
from __future__ import annotations

import html
import smtplib
import urllib.parse
from email.mime.text import MIMEText

import config
import job_time


def _job_url(job: dict) -> str:
    """Prefer the canonical URL now returned by Upwork, with a safe fallback."""
    url = job.get("url")
    if isinstance(url, str) and url.startswith("https://www.upwork.com/"):
        return url

    # Older saved payloads did not include a URL. An exact-title search still
    # gives those alerts a useful destination.
    q = urllib.parse.quote(f'"{job.get("title") or ""}"')
    return f"https://www.upwork.com/nx/search/jobs/?q={q}"


def _client_name(job: dict) -> str | None:
    """Return a name only when Upwork explicitly supplied one.

    Marketplace search normally withholds client identity. Previous-client
    results can contain a company name, and this also accepts likely fields if
    Upwork adds them to the regular client block later. Never guess a person's
    name from the job description.
    """
    client = job.get("client") or {}
    previous = job.get("previous_client") or {}
    for value in (
        job.get("client_name"),
        client.get("name"),
        client.get("client_name"),
        client.get("company_name"),
        previous.get("company_name"),
    ):
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _row(job: dict) -> str:
    c = job.get("client", {})
    title = job.get("title") or "(untitled)"
    budget = job.get("budget")
    money = f"${budget} fixed" if job.get("job_type") == "fixed" else "Hourly"
    props = job.get("proposal_count")
    if props is None:
        props = job.get("proposals_tier", "?")
    reason = job.get("_reason", "")
    score = job.get("_score", "")
    posted = job_time.age_label(job)
    client_name = _client_name(job)
    desc = (job.get("description_snippet") or "").replace("<untrusted_participant_content>", "").replace("</untrusted_participant_content>", "").strip()
    e = html.escape
    client_bits = []
    if client_name:
        client_bits.append(f"Client: {e(client_name)}")
    client_bits.extend([
        e(c.get("country") or "?"),
        f"{e(str(c.get('total_reviews') or 0))} reviews",
        f"rating {e(str(c.get('rating') or 'n/a'))}",
    ])
    client_summary = " &middot; ".join(client_bits)
    return f"""
    <div style="margin:0 0 20px;padding:14px 16px;border:1px solid #e3e3e3;border-radius:10px">
      <div style="font-size:16px;font-weight:600;margin-bottom:4px">
        <a href="{e(_job_url(job), quote=True)}" style="color:#14a800;text-decoration:none">{e(title)}</a>
        <span style="float:right;font-size:12px;color:#888">score {e(str(score))}</span>
      </div>
      <div style="color:#555;font-size:13px;margin-bottom:8px">
        <b>Posted {e(posted)}</b> &middot; {e(money)} &middot; {e(str(props))} proposals &middot;
        {client_summary}
      </div>
      <div style="color:#111;font-size:13px;margin-bottom:8px">{e(desc[:300])}</div>
      <div style="font-size:12px;color:#14a800"><b>Why it fits:</b> {e(reason)}</div>
    </div>"""


def send_digest(jobs: list[dict], extra: int = 0) -> None:
    """Email the newest qualified jobs for this poll (already ranked)."""
    if not jobs:
        return
    if not (config.GMAIL_USER and config.GMAIL_APP_PASSWORD):
        print("[notify] Gmail creds not set — skipping email. Top matches:",
              [j.get("title") for j in jobs])
        return

    first = jobs[0].get("title", "job")
    freshness = f"{config.MAX_JOB_AGE_HOURS:g} hour"
    if config.MAX_JOB_AGE_HOURS != 1:
        freshness += "s"
    subject = f"New Upwork alert — {len(jobs)} match{'es' if len(jobs) > 1 else ''}: {first[:55]}"
    more = (f'<p style="color:#888;font-size:12px">+ {extra} more match(es) queued '
            f'for the next alert (showing top {len(jobs)}).</p>') if extra else ""
    body = f"""<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:640px">
      <p style="font-size:15px">Your newest qualified Upwork match(es):</p>
      {''.join(_row(j) for j in jobs)}
      {more}
      <p style="color:#999;font-size:12px">Upwork Job Alerts &middot; posted within {freshness} &middot; verified client &middot; &lt;5 proposals &middot; AI/automation/Python fit</p>
    </div>"""

    msg = MIMEText(body, "html", "utf-8")
    msg["Subject"] = subject
    msg["From"] = config.GMAIL_USER
    msg["To"] = config.ALERT_TO

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(config.GMAIL_USER, config.GMAIL_APP_PASSWORD)
        s.sendmail(config.GMAIL_USER, [config.ALERT_TO], msg.as_string())
    print(f"[notify] emailed {len(jobs)} job(s) to {config.ALERT_TO}")
