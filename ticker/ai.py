"""The AI editor: classifies entries, writes one-line takeaways and the daily brief.

Uses Google Gemini (free tier) by default, or any OpenAI-compatible endpoint, with the AI_TOKEN secret.
Without a token every step falls back to deterministic rules, so the site never stalls.
"""
import json
import os
import re
import time
import urllib.error
import urllib.request

from .util import clip

CATEGORIES = ("feature", "model", "pricing", "deprecation", "fix")

RULES = [
    ("deprecation", r"\b(deprecat\w*|end of life|retire[ds]?|retirement|sunset\w*|removed|removal|no longer (available|served|supported))\b"),
    ("pricing", r"(\b(pric(e|es|ing)|billing|credits?|quotas?|ACUs?|subscriptions?|discounts?|spend limits?|free tier|paid plans?)\b|\$\d)"),
    ("model", r"\b(models?|gpt-?\d[\w.-]*|o\d-[\w-]+|grok[- ](\d|code|voice|imagine)[\w.-]*|claude (opus|sonnet|haiku)|(opus|sonnet|haiku) \d[\d.]*|gemini|context window)\b"),
    ("fix", r"^(fixed|fixes|fix|bug ?fix(es)?)\b"),
]
RELEASE_TITLE = re.compile(r"^(Claude Code|Codex CLI) \d")


def heuristic_category(title, body, section=None):
    """Judge by the title (bodies mention plans, models and removals in passing); release bundles by their bullets."""
    if section and re.search(r"\bfix", section, re.I):
        return "fix"
    if RELEASE_TITLE.match(title):
        bullets = [l.strip("-•* ").lower() for l in body.splitlines() if l.strip().startswith(("-", "•", "*"))]
        return "fix" if bullets and all(b.startswith("fix") for b in bullets) else "feature"
    for cat, pat in RULES:
        if re.search(pat, title, re.I):
            return cat
    return "feature"


def heuristic_takeaway(entry):
    body = entry.get("body") or ""
    lines = [l.strip("-•* ").strip() for l in body.splitlines() if l.strip()]
    lines = [l for l in lines if not l.endswith(":") and not re.match(r"^(full changelog|what's changed)\b", l, re.I)]
    highlights = [l for l in lines if re.match(r"^(added|new|introduc|you can now|now )", l, re.I)] or lines
    return clip(highlights[0] if highlights else entry["title"], 200)


OPENAI = "https://api.openai.com/v1"
GEMINI = "https://generativelanguage.googleapis.com/v1beta/openai"
GEMINI_MODEL = "gemini-4-hydrogen"


class Editor:
    def __init__(self, token=None, base_url=None, model=None, max_calls=None):
        self.base_url = base_url or os.environ.get("AI_BASE_URL") or GEMINI
        self.model = model or os.environ.get("AI_MODEL") or GEMINI_MODEL
        self.token = token if token is not None else os.environ.get("AI_TOKEN")
        self.max_calls = max_calls if max_calls is not None else int(os.environ.get("AI_MAX_CALLS", "30"))
        self.calls = 0
        self.errors = []
        self.enabled = bool(self.token) and os.environ.get("AI_DISABLED") != "1"

    def chat(self, system, user, max_tokens=1500):
        if not self.enabled or self.calls >= self.max_calls:
            return None
        self.calls += 1
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0.2,
            "max_tokens": max_tokens,
        }
        for attempt in range(3):
            try:
                req = urllib.request.Request(
                    self.base_url.rstrip("/") + "/chat/completions",
                    data=json.dumps(payload).encode(),
                    headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=90) as resp:
                    data = json.load(resp)
                return data["choices"][0]["message"]["content"]
            except urllib.error.HTTPError as exc:
                code = self._error_code(exc)
                if exc.code == 429 and code != "insufficient_quota" and attempt < 2:
                    time.sleep(5 * (attempt + 1))  # rate limit: wait and retry
                    continue
                self.errors.append(f"HTTP {exc.code}: {code}")
                if exc.code in (401, 403) or code == "insufficient_quota":
                    self.enabled = False  # every further call would fail the same way
                return None
            except Exception as exc:  # network or schema: degrade to rules
                self.errors.append(f"{type(exc).__name__}: {clip(str(exc), 160)}")
                return None

    @staticmethod
    def _error_code(exc):
        try:
            err = json.loads(exc.read() or b"{}").get("error") or {}
            return err.get("code") or err.get("type") or clip(err.get("message") or exc.reason, 80)
        except Exception:
            return str(exc.reason)

    @staticmethod
    def _json(text):
        if not text:
            return None
        m = re.search(r"\{.*\}|\[.*\]", text, re.S)
        try:
            return json.loads(m.group(0)) if m else None
        except json.JSONDecodeError:
            return None

    def enrich(self, entries, agent_names, batch=8):
        """Set category, headline and takeaway on each entry (in place)."""
        system = (
            "You edit Agent-Ticker, a daily briefing for vibe coders on AI coding agents. "
            "For each changelog item return JSON {\"items\":[{\"id\":...,\"category\":one of "
            f"{list(CATEGORIES)},\"headline\":max 80 chars plain English,\"takeaway\":max 170 chars on what "
            "it means for someone building apps with this agent}]}. Category 'model' only when an AI model is added, "
            "changed or renamed; 'pricing' only for prices, plans, credits, quotas or billing; 'deprecation' only when "
            "something is deprecated, retired or removed; 'fix' only when the item is bug fixes; otherwise 'feature'. "
            "Keep identifiers such as env vars, flags and model ids exactly as written. "
            "Release notes that bundle many changes: headline the most useful change. Facts only from the text."
        )
        for i in range(0, len(entries), batch):
            chunk = entries[i : i + batch]
            items = [
                {"id": e["id"], "agent": agent_names[e["agent"]], "title": e["title"], "text": clip(e["body"], 900)}
                for e in chunk
            ]
            parsed = self._json(self.chat(system, json.dumps(items, ensure_ascii=False)))
            by_id = {}
            if isinstance(parsed, dict):
                by_id = {str(x.get("id")): x for x in (parsed.get("items") or []) if isinstance(x, dict)}
            for e in chunk:
                got = by_id.get(e["id"])
                if got and got.get("category") in CATEGORIES and all(isinstance(got.get(k) or "", str) for k in ("headline", "takeaway")):
                    e["category"] = got["category"]
                    e["headline"] = clip(got.get("headline") or e["title"], 100)
                    e["takeaway"] = clip(got.get("takeaway") or heuristic_takeaway(e), 220)
                    e["editor"] = "ai"
                else:
                    e["category"] = heuristic_category(e["title"], e["body"], e.get("section"))
                    e["headline"] = e["title"]
                    e["takeaway"] = heuristic_takeaway(e)
                    e["editor"] = "rules"
        return entries

    def brief(self, day, entries, pricing_changes, agent_names):
        """Return {'headline','bullets':[...],'editor'} for one day's news."""
        if not entries and not pricing_changes:
            return {"headline": "Quiet day: no official changes detected.", "bullets": [], "editor": "rules"}
        items = [
            {"agent": agent_names[e["agent"]], "category": e.get("category"), "headline": e.get("headline"), "takeaway": e.get("takeaway")}
            for e in entries[:30]
        ]
        for p in pricing_changes:
            items.append({"agent": agent_names[p["agent"]], "category": "pricing", "added": p["added"][:8], "removed": p["removed"][:8]})
        system = (
            "You write the Agent-Ticker daily brief for vibe coders. Return JSON {\"headline\": max 90 chars, "
            "\"bullets\": 3 to 5 strings, each max 180 chars, starting with the agent name}. Lead with pricing "
            "and model changes, then the most useful features. No hype, no invented facts."
        )
        parsed = self._json(self.chat(system, f"Date: {day}\n" + json.dumps(items, ensure_ascii=False), 700))
        if isinstance(parsed, dict) and isinstance(parsed.get("headline"), str) and isinstance(parsed.get("bullets"), list):
            bullets = [clip(b, 220) for b in parsed["bullets"] if isinstance(b, str)][:5]
            if parsed["headline"].strip() and bullets:
                return {"headline": clip(parsed["headline"], 120), "bullets": bullets, "editor": "ai"}
        order = {"pricing": 0, "model": 1, "deprecation": 2, "feature": 3, "fix": 4}
        ranked = sorted(entries, key=lambda e: order.get(e.get("category"), 5))
        bullets = [f"{agent_names[p['agent']]}: pricing page changed." for p in pricing_changes]
        bullets += [f"{agent_names[e['agent']]}: {e.get('headline') or e['title']}" for e in ranked]
        agents = sorted({agent_names[e["agent"]] for e in entries} | {agent_names[p["agent"]] for p in pricing_changes})
        n = len(entries) + len(pricing_changes)
        return {"headline": f"{n} change{'s' if n != 1 else ''} across {', '.join(agents)}", "bullets": bullets[:5], "editor": "rules"}

    def summarize_pricing(self, agent_name, text):
        """Extract current plans as [{'plan','price','note'}] from a pricing page snapshot."""
        system = (
            "Extract the current paid and free plans from this pricing page text. Return JSON "
            "{\"plans\":[{\"plan\":name,\"price\":as written e.g. '$20/month' or 'Contact sales',\"note\":max 90 chars}]}. "
            "At most 6 plans; for API price tables give the flagship model rows instead. Only facts from the text."
        )
        parsed = self._json(self.chat(system, f"{agent_name} pricing page:\n{clip(text, 6000)}", 700))
        if isinstance(parsed, dict) and isinstance(parsed.get("plans"), list):
            return [
                {"plan": clip(str(p.get("plan", "")), 60), "price": clip(str(p.get("price", "")), 60), "note": clip(str(p.get("note", "")), 110)}
                for p in parsed["plans"][:6]
                if isinstance(p, dict)
            ]
        return None
