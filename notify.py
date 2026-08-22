"""Email the matched jobs via Gmail SMTP."""
from __future__ import annotations

import html
import smtplib
import urllib.parse
from email.mime.text import MIMEText

import config


def _job_url(title: str) -> str:
    # Upwork obfuscates the ciphertext, so link to an exact-title search — lands
    # on the specific post when you're logged in.
    q = urllib.parse.quote(f'"{title}"')
    return f"https://www.upwork.com/nx/search/jobs/?q={q}"


def _row(job: dict) -> str:
    c = job.get("client", {})
    title = job.get("title") or "(untitled)"
    budget = job.get("budget")
    money = f"${budget} fixed" if job.get("job_type") == "fixed" else "Hourly"
    props = job.get("proposal_count", "?")
    reason = job.get("_reason", "")
    score = job.get("_score", "")
    desc = (job.get("description_snippet") or "").replace("<untrusted_participant_content>", "").replace("</untrusted_participant_content>", "").strip()
    e = html.escape
    return f"""
    <div style="margin:0 0 20px;padding:14px 16px;border:1px solid #e3e3e3;border-radius:10px">
      <div style="font-size:16px;font-weight:600;margin-bottom:4px">
        <a href="{_job_url(title)}" style="color:#14a800;text-decoration:none">{e(title)}</a>
        <span style="float:right;font-size:12px;color:#888">score {e(str(score))}</span>
      </div>
      <div style="color:#555;font-size:13px;margin-bottom:8px">
        {e(money)} &middot; {e(str(props))} proposals &middot;
        {e(c.get('country') or '?')} &middot; {e(str(c.get('total_hires') or 0))} hires &middot;
        rating {e(str(c.get('rating') or 'n/a'))}
      </div>
      <div style="color:#111;font-size:13px;margin-bottom:8px">{e(desc[:300])}</div>
      <div style="font-size:12px;color:#14a800"><b>Why it fits:</b> {e(reason)}</div>
    </div>"""


def send_digest(jobs: list[dict], extra: int = 0) -> None:
    """Email the top matched jobs for this digest window (already ranked)."""
    if not jobs:
        return
    if not (config.GMAIL_USER and config.GMAIL_APP_PASSWORD):
        print("[notify] Gmail creds not set — skipping email. Top matches:",
              [j.get("title") for j in jobs])
        return

    first = jobs[0].get("title", "job")
    subject = f"Upwork digest — {len(jobs)} top match{'es' if len(jobs) > 1 else ''}: {first[:55]}"
    more = (f'<p style="color:#888;font-size:12px">+ {extra} more match(es) this window '
            f'not shown (showing top {len(jobs)}).</p>') if extra else ""
    body = f"""<div style="font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:640px">
      <p style="font-size:15px">Your top {len(jobs)} Upwork match(es) since the last digest:</p>
      {''.join(_row(j) for j in jobs)}
      {more}
      <p style="color:#999;font-size:12px">Upwork Job Alerts &middot; filters: verified client, &lt;5 proposals, AI/automation/Python &middot; ranked by fit score</p>
    </div>"""

    msg = MIMEText(body, "html", "utf-8")
    msg["Subject"] = subject
    msg["From"] = config.GMAIL_USER
    msg["To"] = config.ALERT_TO

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(config.GMAIL_USER, config.GMAIL_APP_PASSWORD)
        s.sendmail(config.GMAIL_USER, [config.ALERT_TO], msg.as_string())
    print(f"[notify] emailed {len(jobs)} job(s) to {config.ALERT_TO}")
