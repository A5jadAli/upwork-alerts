import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import main


class PollOnceTests(unittest.TestCase):
    @patch("main.notify.send_digest")
    @patch("main.jobfilter.evaluate")
    @patch("main.mcp_upwork.search_all")
    @patch("main.state")
    def test_new_qualified_job_is_emailed_in_same_poll(
        self, state, search_all, evaluate, send_digest
    ):
        job = {
            "id": "123",
            "title": "Fresh RAG job",
            "published_date": (
                datetime.now(timezone.utc) - timedelta(minutes=4)
            ).isoformat(),
        }
        state.get_access_token.return_value = "token"
        state.load_seen.return_value = set()
        state.load_pending.return_value = {"last_digest_at": None, "jobs": []}
        search_all.return_value = [job]
        evaluate.return_value = {"fit": True, "score": 90, "reason": "strong fit"}

        main.poll_once()

        send_digest.assert_called_once()
        self.assertEqual(send_digest.call_args.args[0][0]["id"], "123")
        self.assertEqual(state.save_pending.call_args.args[0]["jobs"], [])


if __name__ == "__main__":
    unittest.main()
