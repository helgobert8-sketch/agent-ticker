"""Pricing watch: snapshot official pricing pages as text and detect changes."""
import difflib
import os
import re

from .util import fetch, html_to_text, md_to_text

PRICING_PAGES = {
    "devin": "https://devin.ai/pricing",
    "claude-code": "https://claude.com/pricing",
    "codex": "https://developers.openai.com/codex/pricing.md",
    "cursor": "https://cursor.com/pricing",
    "grok": "https://docs.x.ai/docs/models.md",
}

NOISE = re.compile(r"(dpl_[A-Za-z0-9]+|\?[^ )]*&w=\d+[^ )]*|\b\d{10,}\b)")


def normalize(raw):
    looks_html = raw.lstrip().startswith("<")
    text = html_to_text(raw) if looks_html else md_to_text(raw)
    text = NOISE.sub("", text)
    lines = [line.strip() for line in text.splitlines()]
    keep = [line for line in lines if line and len(line) < 400]
    return "\n".join(keep)


def price_lines(text):
    """Lines that carry prices or plan limits; the part of a pricing page worth diffing."""
    pat = re.compile(r"(\$\s?\d|€\s?\d|\d+\s?(?:USD|EUR)|per (?:month|user|seat|year)|/\s?(?:mo|month|1M|million)|credits?|quota|free|plan|tier|tokens?)", re.I)
    return [line for line in text.splitlines() if pat.search(line)]


def diff(old, new, limit=40):
    old_lines, new_lines = price_lines(old), price_lines(new)
    added, removed = [], []
    for line in difflib.ndiff(old_lines, new_lines):
        if line.startswith("+ "):
            added.append(line[2:])
        elif line.startswith("- "):
            removed.append(line[2:])
    return added[:limit], removed[:limit]


def snapshot_path(data_dir, agent):
    return os.path.join(data_dir, "pricing", f"{agent}.txt")


def check(agent, data_dir, raw=None):
    """Return dict(changed, added, removed, text). First snapshot is never a change."""
    raw = raw if raw is not None else fetch(PRICING_PAGES[agent])
    text = normalize(raw)
    path = snapshot_path(data_dir, agent)
    old = open(path).read() if os.path.exists(path) else None
    result = {"agent": agent, "url": PRICING_PAGES[agent], "text": text, "first": old is None}
    if old is None:
        result.update(changed=False, added=[], removed=[])
    else:
        added, removed = diff(old, text)
        result.update(changed=bool(added or removed), added=added, removed=removed)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text + "\n")
    return result
