"""ONE-TIME local login. Run on your own machine:

    CLIENT_ID="https://raw.githubusercontent.com/<user>/<repo>/main/client-metadata.json" \
      python bootstrap.py

Opens Upwork in your browser, you approve, and it:
  1. captures the refresh token  -> save it as the UPWORK_REFRESH_TOKEN GitHub secret
  2. immediately runs the 4 searches to PROVE custom code gets the same results.
"""
import http.server
import json
import secrets
import threading
import urllib.parse
import webbrowser

import auth
import mcp_upwork

_code_holder = {}
_done = threading.Event()


class _Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        qs = urllib.parse.urlparse(self.path)
        if qs.path != "/callback":
            self.send_response(404); self.end_headers(); return
        params = urllib.parse.parse_qs(qs.query)
        _code_holder["code"] = params.get("code", [None])[0]
        _code_holder["state"] = params.get("state", [None])[0]
        _code_holder["error"] = params.get("error", [None])[0]
        self.send_response(200)
        self.send_header("content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h2>Done. You can close this tab and return to the terminal.</h2>")
        _done.set()

    def log_message(self, *a):  # silence
        pass


def main():
    import sys
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except Exception:
        pass
    verifier, challenge = auth.make_pkce()
    state = secrets.token_urlsafe(16)
    url = auth.build_authorize_url(challenge, state)

    server = http.server.HTTPServer(("localhost", 8765), _Handler)
    threading.Thread(target=server.handle_request, daemon=True).start()

    print("\nOpening browser to log in to Upwork...\nIf it doesn't open, paste this:\n")
    print(url, "\n")
    try:
        webbrowser.open(url)
    except Exception:
        pass

    if not _done.wait(timeout=300):
        raise SystemExit("Timed out after 5 min waiting for the browser callback.")
    if _code_holder.get("error"):
        raise SystemExit(f"Authorization failed: {_code_holder['error']}")
    if _code_holder.get("state") != state:
        raise SystemExit("State mismatch — aborting.")

    tokens = auth.exchange_code(_code_holder["code"], verifier)
    refresh_token = tokens.get("refresh_token")
    import time
    tokens["expires_at"] = time.time() + int(tokens.get("expires_in", 86400))
    with open("token.json", "w") as f:
        json.dump(tokens, f, indent=2)
    print("\n=== SUCCESS ===")
    print("Access token acquired. expires_in:", tokens.get("expires_in"))
    print("Tokens saved to token.json (gitignored).")
    if refresh_token:
        print("\nSAVE THIS as the GitHub secret UPWORK_REFRESH_TOKEN:\n")
        print(refresh_token, "\n")
    else:
        print("\n(No refresh_token returned — we'll need to adjust scope/params.)\n")

    print("Now proving find_jobs works from custom code...\n")
    jobs = mcp_upwork.search_all(tokens["access_token"])
    print(f"Retrieved {len(jobs)} jobs across {len(__import__('config').QUERIES)} queries.")
    for j in jobs[:8]:
        print(f"  - {j.get('title')!r}  ${j.get('budget')}  {j.get('job_type')}")


if __name__ == "__main__":
    main()
