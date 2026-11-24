import json
import os
import tempfile
import unittest
from unittest import mock

from ticker import ai, pricing, run, site, sources

FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def fixture(name):
    with open(os.path.join(FIX, name)) as f:
        return f.read()


FAKE = {
    "devin": lambda: sources.parse_devin(fixture("devin_release_notes.md")),
    "grok": lambda: sources.parse_xai(fixture("xai_release_notes.md"), year_hint=2026),
    "cursor": lambda: sources.parse_cursor(fixture("cursor_rss.xml")),
    "claude-code": lambda: sources.parse_github_atom("claude-code", fixture("claude_code_releases.atom")),
    "codex": lambda: sources.parse_github_atom("codex", fixture("codex_releases.atom")),
}


class ParserTests(unittest.TestCase):
    def test_devin_has_dated_items(self):
        items = FAKE["devin"]()
        self.assertGreater(len(items), 10)
        self.assertTrue(all(len(e["published"]) == 10 for e in items))
        self.assertEqual(items[0]["published"], "2026-11-23")

    def test_release_markdown_is_plain_text(self):
        body = sources.parse_github_atom("codex", fixture("codex_releases.atom"))[0]["body"]
        self.assertNotIn("## ", body)
        body = sources.parse_github_atom("codex", "<feed xmlns='http://www.w3.org/2005/Atom'><entry><title>rust-v1.0.0</title>"
            "<link href='https://x'/><updated>2026-11-24T00:00:00Z</updated><content>## Fixes\n- keep oidc.groups_jsonpath intact in the notes</content></entry></feed>")[0]["body"]
        self.assertIn("• keep oidc.groups_jsonpath intact", body)
        self.assertIn("- Pro $20", pricing.normalize("- Pro $20 per month"))

    def test_devin_bold_titles(self):
        items = FAKE["devin"]()
        titles = {e["title"] for e in items}
        self.assertIn("Paste videos into session chat", titles)
        self.assertIn("German UI Language", titles)
        self.assertNotIn("Sessions & Workspace", titles)
        self.assertNotIn("Introducing Access and Sharing", titles)
        scm = next(e for e in items if e["title"] == "SCM access mismatch checker")
        self.assertIn("off by default", scm["body"])
        self.assertEqual({e["published"] for e in items if e["title"] == "German UI Language"}, {"2026-11-13"})

    def test_xai_newest_month_from_last_year(self):
        items = sources.parse_xai(fixture("xai_release_notes.md"), year_hint=2027, month_hint=1)
        self.assertEqual(items[0]["published"], "2026-11-01")

    def test_xai_months_and_years(self):
        items = FAKE["grok"]()
        self.assertEqual(items[0]["published"], "2026-11-01")
        self.assertTrue(any(e["published"].startswith("2025-") for e in items))
        self.assertTrue(all(e["date_precision"] == "month" for e in items))

    def test_cursor_rss(self):
        items = FAKE["cursor"]()
        self.assertEqual(items[0]["title"], "Voice Chat with Agents")
        self.assertIn("voice", items[0]["body"].lower())

    def test_github_atom_skips_prereleases(self):
        items = FAKE["codex"]()
        self.assertTrue(items)
        self.assertFalse(any("alpha" in e["title"] for e in items))

    def test_github_api(self):
        payload = json.dumps([
            {"tag_name": "rust-v1.0.0", "prerelease": False, "body": "## New\n- Added a long enough feature description here", "html_url": "u", "url": "a", "published_at": "2026-11-20T10:00:00Z"},
            {"tag_name": "rust-v1.1.0-alpha.1", "prerelease": True, "body": "x" * 100, "html_url": "u", "url": "a", "published_at": "2026-11-21T10:00:00Z"},
        ])
        items = sources.parse_github_api("codex", payload)
        self.assertEqual([e["title"] for e in items], ["Codex CLI 1.0.0"])


class PricingTests(unittest.TestCase):
    def test_change_detection(self):
        with tempfile.TemporaryDirectory() as d:
            first = pricing.check("devin", d, raw="# Pricing\nPro\n$20 per month\nTeams\n$80 per month")
            self.assertFalse(first["changed"])
            same = pricing.check("devin", d, raw="# Pricing\nPro\n$20 per month\nTeams\n$80 per month")
            self.assertFalse(same["changed"])
            moved = pricing.check("devin", d, raw="# Pricing\nPro\n$25 per month\nTeams\n$80 per month")
            self.assertTrue(moved["changed"])
            self.assertIn("$25 per month", moved["added"])
            self.assertIn("$20 per month", moved["removed"])


class EditorTests(unittest.TestCase):
    def test_rules_fallback_without_token(self):
        ed = ai.Editor(token="")
        items = ed.enrich([{"id": "1", "agent": "grok", "title": "grok-4.7 is available", "body": "New model."}], run.AGENT_NAMES)
        self.assertEqual(items[0]["category"], "model")
        self.assertEqual(items[0]["editor"], "rules")

    def test_ai_response_is_used(self):
        ed = ai.Editor(token="t")
        reply = json.dumps({"items": [{"id": "1", "category": "pricing", "headline": "Pro now $25", "takeaway": "Budget more."}]})
        with mock.patch.object(ed, "chat", return_value=reply):
            items = ed.enrich([{"id": "1", "agent": "devin", "title": "Plans", "body": "..."}], run.AGENT_NAMES)
        self.assertEqual(items[0]["headline"], "Pro now $25")
        self.assertEqual(items[0]["editor"], "ai")


class EditorRobustnessTests(unittest.TestCase):
    def test_bad_ai_shapes_fall_back(self):
        ed = ai.Editor(token="t")
        for reply in ('{"items": null}', '{"items": [{"id": "1", "category": "model", "headline": 5}]}'):
            with mock.patch.object(ed, "chat", return_value=reply):
                items = ed.enrich([{"id": "1", "agent": "grok", "title": "t", "body": "b"}], run.AGENT_NAMES)
            self.assertEqual(items[0]["editor"], "rules")
        with mock.patch.object(ed, "chat", return_value='{"headline": "h", "bullets": [1, null]}'):
            b = ed.brief("2026-11-24", [{"agent": "grok", "title": "t", "headline": "t", "category": "model"}], [], run.AGENT_NAMES)
        self.assertEqual(b["editor"], "rules")

    def test_empty_env_uses_defaults_and_never_leaks_repo_token(self):
        env = {"AI_BASE_URL": "", "AI_MODEL": "", "AI_TOKEN": "", "GITHUB_TOKEN": "gh"}
        with mock.patch.dict(os.environ, env):
            ed = ai.Editor()
        self.assertEqual((ed.base_url, ed.model), (ai.OPENAI, "gpt-4.1-mini"))
        self.assertFalse(ed.enabled)  # the repo token is never sent to an AI endpoint


class PipelineTests(unittest.TestCase):
    def test_two_runs_build_site(self):
        with tempfile.TemporaryDirectory() as d:
            data, out = os.path.join(d, "data"), os.path.join(d, "public")
            with mock.patch.object(sources, "collect", side_effect=lambda a, **kw: FAKE[a]()), \
                 mock.patch.object(pricing, "fetch", return_value="Pro\n$20 per month"), \
                 mock.patch.object(run, "today", return_value="2026-11-24"):
                first = run.run(data, out, backfill_days=30, editor=ai.Editor(token=""))
                brief = json.load(open(os.path.join(data, "briefs.json")))["2026-11-24"]
                second = run.run(data, out, backfill_days=30, editor=ai.Editor(token=""))
            self.assertGreater(first["new"], 10)
            self.assertEqual(second["new"], 0)
            briefs = json.load(open(os.path.join(data, "briefs.json")))
            self.assertEqual(briefs["2026-11-24"], brief)  # same-day rerun keeps the published brief
            for name in ("index.html", "archive.html", "pricing.html", "autonomy.html", "feed.xml", "data.json", "style.css"):
                self.assertTrue(os.path.exists(os.path.join(out, name)), name)
            html = open(os.path.join(out, "index.html")).read()
            self.assertIn("Voice Chat with Agents", html)
            self.assertEqual(len(json.load(open(os.path.join(data, "runs.json")))), 2)


if __name__ == "__main__":
    unittest.main()
