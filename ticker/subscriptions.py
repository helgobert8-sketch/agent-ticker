"""Monitor the subscription map's primary sources and related ticker items."""
import hashlib
import os
import re

from .pricing import NORMALIZE_VERSION, normalize
from .util import fetch, load_json, save_json

BASELINE = "subscription_map_baseline_2026-11-25.json"
MONITOR = "subscription_map_monitor.json"
TICKER_VENDOR = {"claude-code": "claude", "codex": "chatgpt", "grok": "grok", "devin": "devin"}
ROW_TERMS = {
    "price_plans": r"\b(?:pricing|price changes?|subscription tiers?|plan pricing|monthly price)\b",
    "billing_model": r"\b(?:billing|overage|top[ -]?ups?|pay.as.you.go|prepaid credits|usage.based)\b",
    "usage_limits": r"\b(?:rate limits?|usage limits?|quotas?|allowances?|weekly (?:cap|pool|limit))\b",
    "top_model_access": r"\b(?:model (?:access|availability|picker|selection|support)|(?:adds? support|now available) for [^.\n]{0,25}(?:model|opus|sonnet|gpt|grok|swe)|(?:opus|sonnet|fable|gpt|grok|swe)[ -]\d+(?:\.\d+)*\b[^.\n]{0,30}\b(?:available|support|launch|preview))\b",
    "coding_agent": r"\b(?:coding agents?|remote agents?|cloud (?:agents?|sessions?|coding)|local agents?|agent (?:in|for) (?:your |the )?(?:IDE|terminal))\b",
    "always_on_agent": r"\b(?:scheduled (?:tasks?|actions?|runs?|sessions?|automations?|routines?)|scheduling|recurring (?:tasks?|runs?|work)|cloud routines?)\b",
}
ROW_PATTERNS = {row: re.compile(pattern, re.I) for row, pattern in ROW_TERMS.items()}


def load(data_dir):
    return load_json(os.path.join(data_dir, BASELINE), None), load_json(os.path.join(data_dir, MONITOR), {})


def refresh(data_dir, items, day):
    baseline, state = load(data_dir)
    if not baseline:
        return None
    rows = baseline["rows"]
    urls = dict.fromkeys(cell["source_url"] for row in rows.values() for cell in row.values())
    old_sources = state.get("sources", {})
    sources = {}
    for url in urls:
        before = old_sources.get(url, {})
        record = sources[url] = {k: v for k, v in before.items() if k != "error"}
        try:
            content = normalize(fetch(url, timeout=10))
            if not content:
                raise ValueError("No readable text")
        except Exception as exc:
            record["error"] = f"{type(exc).__name__}: {exc}"[:200]
            continue
        digest = hashlib.sha256(content.encode()).hexdigest()
        if before.get("version") == NORMALIZE_VERSION and before["hash"] != digest:
            record["changed"] = day
        record.update(hash=digest, checked=day, version=NORMALIZE_VERSION)

    updates = state.get("updates", {})
    matches = 0
    for item in items:
        vendor = TICKER_VENDOR.get(item["agent"])
        if vendor is None:
            continue
        text = "\n".join((item["title"], item.get("body", "")))
        for row, pattern in ROW_PATTERNS.items():
            cell = rows.get(row, {}).get(vendor)
            if not cell or cell["checked"] > day or not pattern.search(text):
                continue
            updates.setdefault(row, {})[vendor] = {
                "date": day, "id": item["id"], "published": item["published"], "title": item["title"],
            }
            matches += 1

    save_json(os.path.join(data_dir, MONITOR), {"sources": sources, "updates": updates})
    return {"source_pages": len(urls), "failed": sum("error" in record for record in sources.values()), "ticker_matches": matches}
