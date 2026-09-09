import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import mcp_upwork


class SearchAllTests(unittest.TestCase):
    @patch("mcp_upwork.UpworkMCP")
    def test_combines_sources_dedupes_and_rejects_old_jobs(self, mcp_class):
        now = datetime.now(timezone.utc)
        recent_1 = (now - timedelta(minutes=5)).isoformat()
        recent_2 = (now - timedelta(minutes=8)).isoformat()
        old = (now - timedelta(hours=25)).isoformat()
        smart = {"id": "newest", "published_date": recent_1}
        duplicate = {"id": "newest", "published_date": recent_1}
        keyword = {"id": "keyword", "published_date": recent_2}

        mcp = mcp_class.return_value
        mcp.smart_search.return_value = [smart]
        mcp.find_jobs.side_effect = [
            [duplicate, {"id": "old", "published_date": old}],
            [keyword],
            [],
            [],
        ]

        jobs = mcp_upwork.search_all("token")

        self.assertEqual([job["id"] for job in jobs], ["newest", "keyword"])
        mcp.smart_search.assert_called_once()
        self.assertEqual(mcp.find_jobs.call_count, 4)
        mcp.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
