import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ticker import ai, pricing, run, site, sources, subscription_page, subscriptions, util

ROOT = Path(__file__).resolve().parents[1]
DAY = "2026-11-26"


class SubscriptionTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.data = Path(tmp.name) / "data"
        self.data.mkdir()
        self.out = Path(tmp.name) / "site"
        shutil.copy(ROOT / "data" / subscriptions.BASELINE, self.data)

    def test_watch_dedupes_primary_urls_and_preserves_the_baseline(self):
        baseline_path = self.data / subscriptions.BASELINE
        baseline_bytes = baseline_path.read_bytes()
        baseline, _ = subscriptions.load(self.data)
        self.assertEqual(len(baseline["rows"]), 6)
        self.assertTrue(all(len(row) == 5 for row in baseline["rows"].values()))
        url = baseline["rows"]["price_plans"]["claude"]["source_url"]
        self.assertEqual(url, baseline["rows"]["usage_limits"]["claude"]["source_url"])

        with patch.object(subscriptions, "fetch", return_value="<p>Official plan</p>") as fetch:
            initial = subscriptions.refresh(self.data, [], DAY)
        self.assertLess(initial["source_pages"], 30)
        self.assertEqual(fetch.call_count, initial["source_pages"])
        self.assertEqual([call.args[0] for call in fetch.call_args_list].count(url), 1)
        _, first = subscriptions.load(self.data)
        self.assertNotIn("changed", first["sources"][url])
        self.assertEqual(len(first["sources"][url]["hash"]), 64)

        def fetch_page(target, **kwargs):
            if target == url:
                return "<p>Updated official plan</p>"
            if "10291617" in target:
                raise util.RobotsDisallowed("fixture")
            return "<p>Official plan</p><script>Noise</script>"

        with patch.object(subscriptions, "fetch", side_effect=fetch_page):
            for day in ("2026-11-27", "2026-11-28"):
                self.assertEqual(subscriptions.refresh(self.data, [], day)["failed"], 1)
        _, later = subscriptions.load(self.data)
        self.assertEqual(later["sources"][url]["changed"], "2026-11-27")
        self.assertEqual(later["sources"][url]["checked"], "2026-11-28")
        unavailable = baseline["rows"]["always_on_agent"]["chatgpt"]["source_url"]
        self.assertIn("RobotsDisallowed", later["sources"][unavailable]["error"])
        self.assertEqual(first["sources"][unavailable]["hash"], later["sources"][unavailable]["hash"])
        self.assertEqual(baseline_path.read_bytes(), baseline_bytes)
        site.build(self.data, self.out)
        page = (self.out / "subscriptions.html").read_text()
        self.assertEqual(page.count("Source changed, check"), 2)
        self.assertEqual(page.count("Source scan unavailable"), 1)

    def test_daily_pipeline_links_a_new_item_to_its_cell_only(self):
        linked = sources.entry("claude-code", "Scheduled tasks", "Set up your work.", "https://example.org/claude", DAY, "fixture")
        ignored = sources.entry("cursor", "Scheduled tasks", "Not a map vendor.", "https://example.org/cursor", DAY, "fixture")
        unrelated = sources.entry("claude-code", "Shell bug", "Fixed a crash.", "https://example.org/other", DAY, "fixture")
        with patch.object(sources, "collect", side_effect=[[linked, unrelated], [ignored], [], []]), \
             patch.object(pricing, "fetch", return_value="Pro $20"), \
             patch.object(subscriptions, "fetch", return_value="Official plan"), \
             patch.object(run, "today", return_value=DAY):
            for expected in (1, 0):
                log = run.run(self.data, self.out, agents=["claude-code", "cursor"], editor=ai.Editor(token=""))
                self.assertEqual(log["subscription_map"]["ticker_matches"], expected)
                self.assertEqual(log["ai_calls"], 0)

        page = (self.out / "subscriptions.html").read_text()
        ticker_day = (self.out / f"day-{DAY}.html").read_text()
        self.assertEqual(page.count('class="map-cell"'), 30)
        self.assertEqual(page.count("New update, check"), 1)
        self.assertIn(f'href="day-{DAY}.html#item-{linked["id"]}"', page)
        self.assertIn(f'id="item-{linked["id"]}"', ticker_day)
        self.assertIn('href="subscriptions.html"', ticker_day)
        self.assertIn('data-vendor="claude" data-status="verified" data-verified="false"', page)
        for url in ("https://help.openai.com/en/articles/9793128-about-chatgpt-pro-tiers",
                    "https://openai.com/index/introducing-chatgpt-go/"):
            self.assertIn(f'data-map-source href="{url}"', page)

    def test_baseline_grok_evidence_is_scoped_to_the_checked_tiers(self):
        baseline, _ = subscriptions.load(self.data)
        tiers = baseline["meta"]["tiers"]["grok"]
        for row in ("top_model_access", "coding_agent"):
            status = baseline["rows"][row]["grok"]["status"]
            evidence = subscription_page.tier_evidence(row, "grok", status, tiers)
            self.assertTrue(all(evidence[tier] == "not checked" for tier in tiers["legacy"]))
            self.assertEqual(evidence["The X Subscription Premium"], "conditional")
        status = baseline["rows"]["always_on_agent"]["grok"]["status"]
        evidence = subscription_page.tier_evidence("always_on_agent", "grok", status, tiers)
        self.assertEqual(evidence["SuperGrok Lite"], "not included")
        self.assertEqual(evidence["SuperGrok Heavy"], "conditional")

    @unittest.skipUnless(shutil.which("node"), "Node is needed to exercise the browser comparison rules")
    def test_stack_comparison(self):
        subprocess.run(["node", "--test", "tests/subscriptions.test.cjs"], cwd=ROOT, check=True, capture_output=False)
