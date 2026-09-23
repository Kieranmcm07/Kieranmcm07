import tempfile
import unittest
from pathlib import Path
from urllib.error import URLError
from xml.etree import ElementTree

from scripts.update_stats import collect_stats, render_card, update_cards


class StatsTests(unittest.TestCase):
    def test_pagination_and_forks_do_not_inflate_earned_stars(self):
        original = {"fork": False, "private": False, "stargazers_count": 2, "forks_count": 1}
        fork = {"fork": True, "private": False, "stargazers_count": 100, "forks_count": 50}
        responses = iter([
            {"login": "example", "public_repos": 101, "followers": 7},
            [original] * 99 + [fork],
            [original],
        ])
        paths = []

        def fetch(path):
            paths.append(path)
            return next(responses)

        stats = collect_stats("example", fetch)
        self.assertEqual(stats["repositories"], 101)
        self.assertEqual(stats["stars"], 200)
        self.assertEqual(stats["forks"], 100)
        self.assertTrue(paths[-1].endswith("page=2"))

    def test_failed_fetch_preserves_both_cached_cards(self):
        with tempfile.TemporaryDirectory() as directory:
            for theme in ("dark", "light"):
                Path(directory, f"github-stats-{theme}.svg").write_text("last good card")

            def fail(path):
                raise URLError("service unavailable")

            with self.assertRaises(URLError):
                update_cards("example", directory, fail)
            for theme in ("dark", "light"):
                self.assertEqual(Path(directory, f"github-stats-{theme}.svg").read_text(), "last good card")

    def test_new_profile_has_valid_zero_cards_in_both_themes(self):
        responses = iter([{"login": "example", "public_repos": 0, "followers": 0}, []])
        with tempfile.TemporaryDirectory() as directory:
            stats = update_cards("example", directory, lambda path: next(responses))
            self.assertEqual(stats["stars"], 0)
            self.assertEqual(stats["forks"], 0)
            for theme in ("dark", "light"):
                ElementTree.parse(Path(directory, f"github-stats-{theme}.svg"))


if __name__ == "__main__":
    unittest.main()
