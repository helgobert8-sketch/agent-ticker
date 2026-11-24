"""Collectors for official changelogs. Each returns a list of entry dicts."""
import json
import re
import xml.etree.ElementTree as ET

from .util import clip, fetch, github_headers, html_to_text, md_to_text, parse_date, stable_id

ATOM = {"a": "http://www.w3.org/2005/Atom"}
CONTENT = "{http://purl.org/rss/1.0/modules/content/}encoded"

AGENTS = {
    "devin": {"name": "Devin", "maker": "Cognition", "home": "https://devin.ai"},
    "claude-code": {"name": "Claude Code", "maker": "Anthropic", "home": "https://claude.com/product/claude-code"},
    "codex": {"name": "Codex", "maker": "OpenAI", "home": "https://developers.openai.com/codex"},
    "cursor": {"name": "Cursor", "maker": "Anysphere", "home": "https://cursor.com"},
    "grok": {"name": "Grok", "maker": "xAI", "home": "https://docs.x.ai"},
}

SOURCES = {
    "devin": "https://docs.devin.ai/release-notes/overview.md",
    "claude-code": "https://github.com/anthropics/claude-code/releases.atom",
    "codex": "https://github.com/openai/codex/releases.atom",
    "cursor": "https://cursor.com/changelog/rss.xml",
    "grok": "https://docs.x.ai/docs/release-notes.md",
}

GITHUB_RELEASES_API = {
    "claude-code": "https://api.github.com/repos/anthropics/claude-code/releases?per_page=30",
    "codex": "https://api.github.com/repos/openai/codex/releases?per_page=60",
}

PRERELEASE = re.compile(r"(alpha|beta|rc|preview|nightly)", re.I)

MONTHS = "January February March April May June July August September October November December".split()


def entry(agent, title, body, url, published, source, precision="day"):
    return {
        "id": stable_id(agent, title.strip(), published or ""),
        "agent": agent,
        "title": clip(title, 160),
        "body": clip(body, 1500),
        "url": url,
        "published": published,
        "date_precision": precision,
        "source": source,
    }


def parse_devin(md, url="https://docs.devin.ai/release-notes/overview"):
    out, current_date = [], None
    blocks = re.split(r"^(?=\*\*[A-Z][a-z]+ \d{1,2}, \d{4}\*\*|#{2,3} )", md, flags=re.M)
    section = None
    for block in blocks:
        head, _, rest = block.partition("\n")
        m = re.match(r"\*\*([A-Z][a-z]+ \d{1,2}, \d{4})\*\*", head)
        if m:
            current_date = parse_date(m.group(1))
            continue
        if head.startswith("## "):
            section = head[3:].strip()
            continue
        if head.startswith("### ") and current_date:
            title = head[4:].strip()
            body = md_to_text(rest)
            e = entry("devin", title, body, url, current_date, SOURCES["devin"])
            e["section"] = section
            out.append(e)
    return out


def parse_xai(md, url="https://docs.x.ai/docs/release-notes", year_hint=None):
    out, month, year = [], None, year_hint
    for block in re.split(r"^(?=#{2,3} )", md, flags=re.M):
        head, _, rest = block.partition("\n")
        if head.startswith("## "):
            name = head[3:].strip()
            m = re.match(r"([A-Z][a-z]+)(?: (\d{4}))?$", name)
            if m and m.group(1) in MONTHS:
                if month and MONTHS.index(m.group(1)) > MONTHS.index(month) and year:
                    year -= 1  # list runs newest first; wrapping past January means the year before
                month = m.group(1)
                if m.group(2):
                    year = int(m.group(2))
            continue
        if head.startswith("### ") and month and year:
            published = f"{year}-{MONTHS.index(month) + 1:02d}-01"
            title = head[4:].strip()
            e = entry("grok", title, md_to_text(rest), url, published, SOURCES["grok"], precision="month")
            e["id"] = stable_id("grok", title)
            out.append(e)
    return out


def parse_cursor(xml_text):
    out = []
    root = ET.fromstring(xml_text)
    for item in root.iter("item"):
        title = item.findtext("title") or ""
        link = item.findtext("link") or "https://cursor.com/changelog"
        published = parse_date(item.findtext("pubDate") or "")
        html_body = item.findtext(CONTENT) or item.findtext("description") or ""
        out.append(entry("cursor", title, html_to_text(html_body), link, published, SOURCES["cursor"]))
    return out


def _release_title(agent, tag):
    name = {"claude-code": "Claude Code", "codex": "Codex CLI"}[agent]
    version = re.sub(r"^(rust-)?v?", "", tag)
    return f"{name} {version}"


def parse_github_atom(agent, xml_text):
    out = []
    for e in ET.fromstring(xml_text).findall("a:entry", ATOM):
        tag = e.findtext("a:title", "", ATOM)
        if PRERELEASE.search(tag):
            continue
        link = e.find("a:link", ATOM).get("href")
        body = html_to_text(e.findtext("a:content", "", ATOM))
        if len(body) < 40:
            continue
        published = parse_date(e.findtext("a:updated", "", ATOM))
        out.append(entry(agent, _release_title(agent, tag), body, link, published, SOURCES[agent]))
    return out


def parse_github_api(agent, json_text):
    out = []
    for r in json.loads(json_text):
        if r.get("prerelease") or r.get("draft") or PRERELEASE.search(r.get("tag_name", "")):
            continue
        body = md_to_text(r.get("body") or "")
        if len(body) < 40:
            continue
        published = parse_date(r.get("published_at") or r.get("created_at") or "")
        out.append(entry(agent, _release_title(agent, r["tag_name"]), body, r["html_url"], published, r["url"]))
    return out


def collect(agent, year_hint=None):
    """Fetch one agent's official changelog. Raises on network/parse failure."""
    if agent == "devin":
        return parse_devin(fetch(SOURCES[agent]))
    if agent == "grok":
        return parse_xai(fetch(SOURCES[agent]), year_hint=year_hint)
    if agent == "cursor":
        return parse_cursor(fetch(SOURCES[agent]))
    if agent in GITHUB_RELEASES_API:
        try:
            return parse_github_api(agent, fetch(GITHUB_RELEASES_API[agent], headers=github_headers()))
        except Exception:
            return parse_github_atom(agent, fetch(SOURCES[agent]))
    raise KeyError(agent)
