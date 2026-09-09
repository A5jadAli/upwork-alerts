import unittest
from datetime import datetime, timezone

import job_time


class JobTimeTests(unittest.TestCase):
    NOW = datetime(2026, 9, 9, 8, 0, tzinfo=timezone.utc)

    def test_accepts_job_inside_24_hour_window(self):
        job = {"published_date": "2026-09-09T07:42:00Z"}

        self.assertTrue(job_time.is_recent(job, 24, self.NOW))
        self.assertEqual(job_time.age_label(job, self.NOW), "18 min ago")

    def test_rejects_old_or_undated_job(self):
        old = {"published_date": "2026-09-08T07:59:59Z"}

        self.assertFalse(job_time.is_recent(old, 24, self.NOW))
        self.assertFalse(job_time.is_recent({}, 24, self.NOW))

    def test_falls_back_to_created_date(self):
        job = {"published_date": "invalid", "created_date": "2026-09-09T07:00:00Z"}

        self.assertEqual(job_time.published_at(job).hour, 7)


if __name__ == "__main__":
    unittest.main()
