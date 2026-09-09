import unittest
from datetime import datetime, timedelta, timezone

import notify


class NotifyRowTests(unittest.TestCase):
    def test_uses_canonical_upwork_url_and_previous_client_company(self):
        job = {
            "title": "Build an automation",
            "url": "https://www.upwork.com/jobs/~02123",
            "job_type": "hourly",
            "published_date": (
                datetime.now(timezone.utc) - timedelta(minutes=8)
            ).isoformat(),
            "proposal_count": 2,
            "client": {"country": "US", "rating": 5, "total_reviews": 3},
            "previous_client": {"company_name": "Example & Co"},
        }

        row = notify._row(job)

        self.assertIn('href="https://www.upwork.com/jobs/~02123"', row)
        self.assertIn("Client: Example &amp; Co", row)
        self.assertIn("3 reviews", row)
        self.assertIn("Posted 8 min ago", row)
        self.assertNotIn("hires", row)

    def test_does_not_guess_a_name_and_falls_back_to_title_search(self):
        job = {
            "title": "Need help from John",
            "job_type": "fixed",
            "budget": 100,
            "client": {"country": "CA"},
        }

        row = notify._row(job)

        self.assertNotIn("Client:", row)
        self.assertIn("https://www.upwork.com/nx/search/jobs/?q=", row)

    def test_uses_smart_search_proposal_tier(self):
        job = {
            "title": "Recent document AI job",
            "job_type": "hourly",
            "proposals_tier": "Less than 5",
            "published_date": datetime.now(timezone.utc).isoformat(),
        }

        row = notify._row(job)

        self.assertIn("Less than 5 proposals", row)


if __name__ == "__main__":
    unittest.main()
