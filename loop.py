"""Always-on runner: poll every POLL_INTERVAL_SECONDS, forever, resiliently.

Use this on a VPS / container / free VM. For a cron-based host instead, run
`python main.py` on a schedule.
"""
import time
import traceback

import config
import main

if __name__ == "__main__":
    print(f"Upwork Job Alerts running — polling every {config.POLL_INTERVAL_SECONDS}s.")
    while True:
        try:
            main.poll_once()
        except Exception:
            traceback.print_exc()
        time.sleep(config.POLL_INTERVAL_SECONDS)
