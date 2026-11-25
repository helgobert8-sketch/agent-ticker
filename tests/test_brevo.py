import json
import os
import tempfile
import unittest
from unittest import mock

from ticker import brevo, site
from ticker.util import save_json


BRIEF = {
    "headline": "Codex extends free Sites hosting",
    "bullets": ["Codex: Sites hosting is free.", "Devin: Bots gain automation controls."],
    "editor": "ai",
    "count": 2,
}


class BrevoTests(unittest.TestCase):
    def write_brief(self, data):
        os.makedirs(data, exist_ok=True)
        save_json(os.path.join(data, "briefs.json"), {"2026-11-25": BRIEF})

    def test_campaign_html_has_brief_links_and_unsubscribe(self):
        page = brevo.campaign_html("2026-11-25", BRIEF, "https://example.test")
        self.assertIn("Codex: Sites hosting is free.", page)
        self.assertIn("https://example.test/day-2026-11-25.html", page)
        self.assertIn('href="{{ unsubscribe }}"', page)
        self.assertIn("Read all 2 changes", page)

    def test_missing_key_skips_without_touching_state(self):
        with tempfile.TemporaryDirectory() as d:
            self.write_brief(d)
            result = brevo.send_daily_brief(d, "2026-11-25", key="")
            self.assertEqual(result["status"], "skipped")
            self.assertFalse(os.path.exists(os.path.join(d, "newsletter.json")))

    def test_send_creates_one_campaign_and_second_run_dedupes(self):
        calls = []

        def fake_api(key, method, path, payload=None, timeout=20):
            calls.append((method, path, payload))
            if method == "GET" and path.startswith("/emailCampaigns?"):
                return {"campaigns": [{"id": 42, "name": brevo.campaign_name("2026-11-25"), "status": "sent"}] if any(c[1] == "/emailCampaigns" for c in calls) else []}
            if path.startswith("/contacts/lists"):
                return {"lists": [{"id": 9, "name": "Other list"}, {"id": 7, "name": "Agent-Ticker Daily"}]}
            if path == "/senders":
                return {"senders": [{"id": 3, "email": "news@example.com", "name": "Agent-Ticker", "active": True, "ips": []}]}
            if method == "POST" and path == "/emailCampaigns":
                return {"id": 42}
            if method == "POST" and path == "/emailCampaigns/42/sendNow":
                return {}
            if method == "GET" and path.startswith("/emailCampaigns/42"):
                return {"id": 42, "name": brevo.campaign_name("2026-11-25"), "status": "sent", "sentDate": "2026-11-25T22:00:00.000Z", "recipients": {"lists": [7]}, "statistics": {"globalStats": {"sent": 1}}}
            raise AssertionError((method, path))

        with tempfile.TemporaryDirectory() as d:
            self.write_brief(d)
            with mock.patch.object(brevo, "api", side_effect=fake_api):
                first = brevo.send_daily_brief(d, "2026-11-25", key="k")
                second = brevo.send_daily_brief(d, "2026-11-25", key="k")
            self.assertEqual((first["status"], first["id"], first["recipients"]), ("sent", 42, 1))
            self.assertEqual(second["status"], "skipped")
            self.assertEqual(second["reason"], "campaign already exists")
            self.assertEqual(sum(1 for m, p, _ in calls if m == "POST" and p == "/emailCampaigns"), 1)
            self.assertEqual(sum(1 for m, p, _ in calls if m == "POST" and p == "/emailCampaigns/42/sendNow"), 1)
            state = json.load(open(os.path.join(d, "newsletter.json")))
            self.assertEqual(state["list"], {"id": 7, "name": "Agent-Ticker Daily"})
            self.assertEqual(state["campaigns"]["2026-11-25"]["status"], "sent")

    def test_existing_draft_is_sent_without_creating_another_campaign(self):
        posts = []

        def fake_api(key, method, path, payload=None, timeout=20):
            if method == "GET" and path.startswith("/emailCampaigns?"):
                return {"campaigns": [{"id": 42, "name": brevo.campaign_name("2026-11-25"), "status": "draft"}]}
            if method == "POST":
                posts.append(path)
                return {} if path.endswith("/sendNow") else {"id": 99}
            if method == "GET" and path.startswith("/emailCampaigns/42"):
                return {"id": 42, "name": brevo.campaign_name("2026-11-25"), "status": "queued", "recipients": {"lists": [7]}, "statistics": {"globalStats": {"sent": 0}}}
            return {"lists": [], "senders": []}

        with tempfile.TemporaryDirectory() as d:
            self.write_brief(d)
            with mock.patch.object(brevo, "api", side_effect=fake_api):
                result = brevo.send_daily_brief(d, "2026-11-25", key="k")
            self.assertEqual(result["status"], "sent")
            self.assertIn("/emailCampaigns/42/sendNow", posts)
            self.assertNotIn("/emailCampaigns", posts)

    def test_brevo_outage_is_reported_not_raised(self):
        with tempfile.TemporaryDirectory() as d:
            self.write_brief(d)
            with mock.patch.object(brevo, "api", side_effect=brevo.BrevoError("HTTP 503: down")):
                result = brevo.send_daily_brief(d, "2026-11-25", key="k")
            self.assertEqual(result["status"], "error")
            self.assertIn("HTTP 503", result["error"])
            state = json.load(open(os.path.join(d, "newsletter.json")))
            self.assertIn("HTTP 503", state["campaigns"]["2026-11-25"]["error"])

    def test_configured_list_name_overrides_saved_list(self):
        lists = {"lists": [{"id": 1, "name": "Old list"}, {"id": 2, "name": "New list"}]}
        with mock.patch.object(brevo, "api", return_value=lists), \
             mock.patch.dict(os.environ, {"BREVO_LIST_ID": "", "BREVO_LIST_NAME": "New list"}):
            self.assertEqual(brevo.choose_list("k", {"list": {"id": 1}})["id"], 2)

    def test_contact_list_search_pages_past_the_first_50(self):
        first = [{"id": n, "name": f"List {n}"} for n in range(50)]
        second = [{"id": 51, "name": "Agent-Ticker Daily"}]
        calls = []

        def fake_api(key, method, path, payload=None, timeout=20):
            calls.append(path)
            return {"count": 51, "lists": second if "offset=50" in path else first}

        env = {"BREVO_LIST_ID": "", "BREVO_LIST_NAME": ""}
        with mock.patch.object(brevo, "api", side_effect=fake_api), mock.patch.dict(os.environ, env):
            self.assertEqual(brevo.choose_list("k", {})["id"], 51)
        self.assertEqual(len(calls), 2)

    def test_automatic_list_choice_never_uses_an_unmatched_or_ambiguous_list(self):
        env = {"BREVO_LIST_ID": "", "BREVO_LIST_NAME": ""}
        with mock.patch.dict(os.environ, env):
            with mock.patch.object(brevo, "api", return_value={"lists": [{"id": 1, "name": "Customers"}]}):
                with self.assertRaises(brevo.BrevoError):
                    brevo.choose_list("k", {})
            ambiguous = {"lists": [{"id": 1, "name": "Agent-Ticker Subscribers"}, {"id": 2, "name": "Agent Ticker Newsletter"}]}
            with mock.patch.object(brevo, "api", return_value=ambiguous):
                with self.assertRaises(brevo.BrevoError):
                    brevo.choose_list("k", {})

    def test_sender_falls_back_when_restricted_key_cannot_read_senders(self):
        env = {"BREVO_SENDER_ID": "", "BREVO_SENDER_EMAIL": ""}
        with mock.patch.object(brevo, "api", side_effect=brevo.BrevoError('HTTP 403 permission_denied: api key is not authorized for resource "account"')), \
             mock.patch.dict(os.environ, env):
            self.assertEqual(brevo.choose_sender("k", {}), brevo.FALLBACK_SENDER)

    def test_list_status_counts_deliverable_contacts_without_exposing_addresses(self):
        def fake_api(key, method, path, payload=None, timeout=20):
            if path.startswith("/contacts/lists?"):
                return {"lists": [{"id": 7, "name": "Agent-Ticker Daily"}]}
            if path.startswith("/contacts/lists/7/contacts"):
                return {
                    "count": 3,
                    "contacts": [
                        {"id": 1, "email": "one@example.com", "emailBlacklisted": False, "listUnsubscribed": []},
                        {"id": 2, "email": "two@example.com", "emailBlacklisted": True, "listUnsubscribed": []},
                        {"id": 3, "emailBlacklisted": False, "listUnsubscribed": []},
                    ],
                }
            raise AssertionError((method, path))

        with tempfile.TemporaryDirectory() as d, \
             mock.patch.object(brevo, "api", side_effect=fake_api), \
             mock.patch.dict(os.environ, {"BREVO_LIST_ID": "", "BREVO_LIST_NAME": ""}):
            result = brevo.list_status(d, key="k")
        self.assertEqual((result["status"], result["contacts"], result["deliverableContacts"]), ("ok", 3, 1))
        self.assertNotIn("email", json.dumps(result))

    def test_signup_slot_is_hidden_until_url_is_configured(self):
        with mock.patch.dict(os.environ, {"BREVO_SIGNUP_URL": ""}):
            self.assertNotIn("Sign up for the newsletter", site.follow_html())
        with mock.patch.dict(os.environ, {"BREVO_SIGNUP_URL": "https://app.brevo.example/form"}):
            page = site.follow_html()
            self.assertIn("Sign up for the newsletter", page)
            self.assertIn("https://app.brevo.example/form", page)
        with mock.patch.dict(os.environ, {"BREVO_SIGNUP_URL": ""}):
            self.assertIn("https://app.brevo.example/stored", site.follow_html("https://app.brevo.example/stored"))


if __name__ == "__main__":
    unittest.main()
