"""Static site builder: index, daily archive, pricing, autonomy log, RSS and JSON."""
import html
import json
import os
import shutil
from collections import OrderedDict
from datetime import date, datetime, timezone
from email.utils import format_datetime

from urllib.parse import quote

from .pricing import PRICING_PAGES
from .sources import AGENTS
from .util import load_json

SITE_URL = os.environ.get("SITE_URL", "https://helgobert8-sketch.github.io/agent-ticker").rstrip("/")
REPO_URL = "https://github.com/helgobert8-sketch/agent-ticker"
CAT_LABEL = {"feature": "Feature", "model": "Model", "pricing": "Pricing", "deprecation": "Removed", "fix": "Fix"}
E_ = html.escape


def nice_date(d, precision="day"):
    dt = date.fromisoformat(d)
    return dt.strftime("%B %Y") if precision == "month" else dt.strftime("%a, %b %-d, %Y")


def page(title, body, active, description="What changed today at Devin, Claude Code, Codex, Cursor and Grok."):
    nav = "".join(
        f'<a href="{href}"{" class=on" if key == active else ""}>{label}</a>'
        for key, href, label in [("home", "index.html", "Today"), ("archive", "archive.html", "Archive"), ("pricing", "pricing.html", "Pricing"), ("autonomy", "autonomy.html", "How it runs")]
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E_(title)}</title><meta name="description" content="{E_(description)}">
<meta property="og:title" content="{E_(title)}"><meta property="og:description" content="{E_(description)}">
<meta property="og:type" content="website"><meta property="og:url" content="{SITE_URL}/"><meta property="og:image" content="{SITE_URL}/og.png">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="{SITE_URL}/og.png">
<link rel="alternate" type="application/rss+xml" title="Agent-Ticker" href="feed.xml">
<link rel="stylesheet" href="style.css"></head>
<body><header><div class="wrap bar"><a class="logo" href="index.html"><span class="dot"></span>Agent-Ticker</a><nav>{nav}</nav></div></header>
<main class="wrap">{body}</main>
<footer class="wrap"><p>Agent-Ticker is written and published every day by an AI editor from official changelogs, release notes and pricing pages only.
Not affiliated with any vendor. <a href="feed.xml">RSS</a> · <a href="data.json">JSON</a> · <a href="{REPO_URL}">Source</a> ·
<a href="{REPO_URL}/issues/new?title=Sponsor%20Agent-Ticker">Sponsor a day</a></p></footer>
<script src="app.js"></script></body></html>"""


def entry_link(e):
    """Devin and xAI publish one long page; a text fragment jumps to the item on it."""
    if e["agent"] in ("devin", "grok") and not e.get("pricing") and "#" not in e["url"]:
        return f'{e["url"]}#:~:text={quote(e["title"][:80], safe="")}'
    return e["url"]


def entry_html(e):
    a = AGENTS[e["agent"]]
    cat = e.get("category", "feature")
    when = nice_date(e["published"], e.get("date_precision", "day"))
    return f"""<article class="item" data-agent="{e['agent']}" data-cat="{cat}">
<div class="meta"><span class="agent a-{e['agent']}">{E_(a['name'])}</span><span class="cat c-{cat}">{CAT_LABEL.get(cat, cat)}</span><time>{when}</time></div>
<h3><a href="{E_(entry_link(e))}" rel="noopener">{E_(e.get('headline') or e['title'])}</a></h3>
<p>{E_(e.get('takeaway') or '')}</p></article>"""


def filters():
    agents = "".join(f'<button data-agent="{k}" class="chip a-{k}">{E_(v["name"])}</button>' for k, v in AGENTS.items())
    cats = "".join(f'<button data-cat="{k}" class="chip">{v}</button>' for k, v in CAT_LABEL.items())
    return f'<div class="filters"><button class="chip on" data-all>All</button>{agents}<span class="sep"></span>{cats}</div>'


def brief_html(day, brief, link=False):
    bullets = "".join(f"<li>{E_(b)}</li>" for b in brief.get("bullets", []))
    shown, count = len(brief.get("bullets", [])), brief.get("count") or 0
    if count > shown and shown:
        bullets += f'<li class="more"><a href="day-{day}.html">Top {shown} of {count}: see all {count} changes</a></li>'
    title = f'<a href="day-{day}.html">{E_(brief["headline"])}</a>' if link else E_(brief["headline"])
    by = "AI editor" if brief.get("editor") == "ai" else "rule-based editor"
    return f"""<section class="brief"><div class="kicker">Daily brief · {nice_date(day)} · by the {by}</div>
<h2>{title}</h2>{f'<ul>{bullets}</ul>' if bullets else ''}</section>"""


def follow_html():
    feed = f"{SITE_URL}/feed.xml"
    share = quote(f"What changed in your AI coding agents today: {SITE_URL}/", safe="")
    return f"""<section class="follow" id="follow"><h2>Follow Agent-Ticker</h2>
<p>Paste the feed address into any RSS reader (Feedly, Inoreader, NetNewsWire, Slack's /feed) and the daily brief and every new change arrive by themselves.</p>
<div class="copy"><input id="feed-url" readonly value="{feed}"><button class="btn" data-copy="{feed}">Copy feed URL</button></div>
<p class="cta"><a class="btn ghost" href="{REPO_URL}">Star or watch on GitHub</a><a class="btn ghost" href="https://x.com/intent/post?text={share}" rel="noopener">Share on X</a>
<button class="btn ghost" data-copy="{SITE_URL}/">Copy link</button></p></section>"""


def tape(entries):
    latest = entries[:12]
    items = "".join(f'<span><b class="a-{e["agent"]}">{E_(AGENTS[e["agent"]]["name"])}</b> {E_(e.get("headline") or e["title"])}</span>' for e in latest)
    return f'<div class="tape" aria-hidden="true"><div class="tape-in">{items}{items}</div></div>'


def stale_attr(last, days=7):
    """Agents quiet for a week get a note shown above their filtered timeline."""
    if not last or (date.today() - date.fromisoformat(last["published"])).days < days:
        return ""
    return f' data-stale="No changes since {nice_date(last["published"], last.get("date_precision", "day"))}."'


def last_change_by_agent(entries):
    out = {}
    for e in entries:
        out.setdefault(e["agent"], e)
    return out


def build(data_dir="data", out_dir="public"):
    entries = load_json(os.path.join(data_dir, "entries.json"), [])
    briefs = load_json(os.path.join(data_dir, "briefs.json"), {})
    plans = load_json(os.path.join(data_dir, "plans.json"), {})
    runs = load_json(os.path.join(data_dir, "runs.json"), [])
    os.makedirs(out_dir, exist_ok=True)
    static = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
    for name in os.listdir(static):
        shutil.copy(os.path.join(static, name), os.path.join(out_dir, name))

    by_day = OrderedDict()
    for e in sorted(entries, key=lambda e: e["published"], reverse=True):
        by_day.setdefault(e["published"], []).append(e)
    days = sorted(set(briefs) | set(by_day), reverse=True)
    latest_brief_day = max(briefs) if briefs else None

    last = last_change_by_agent(entries)
    cards = "".join(
        f'<a class="card a-border-{k}" href="index.html?agent={k}#timeline" data-jump="{k}"{stale_attr(last.get(k))}><span class="agent a-{k}">{E_(v["name"])}</span>'
        f'<small>{E_(v["maker"])}</small><span class="last">{("Last change " + nice_date(last[k]["published"], last[k].get("date_precision","day"))) if k in last else "No changes yet"}</span></a>'
        for k, v in AGENTS.items()
    )
    recent = [e for e in entries if e["published"] >= min(by_day)[:10]] if entries else []
    timeline = []
    for d, items in list(by_day.items())[:40]:
        precision = items[0].get("date_precision", "day")
        timeline.append(f'<section class="day"><h4>{nice_date(d, precision)}</h4>{"".join(entry_html(e) for e in items)}</section>')
    hero = f"""<section class="hero"><h1>What changed in your AI coding agents today.</h1>
<p>Features, models and pricing from <b>Devin</b>, <b>Claude Code</b>, <b>Codex</b>, <b>Cursor</b> and <b>Grok</b>, read from official changelogs every morning and explained in one line each.</p>
<p class="cta"><a class="btn" href="#follow">Follow the ticker</a><a class="btn ghost" href="autonomy.html">See how the AI runs it</a></p></section>"""
    body = hero + (tape(entries) if entries else "")
    if latest_brief_day:
        body += brief_html(latest_brief_day, briefs[latest_brief_day])
    body += f'<section class="cards">{cards}</section>{filters()}<p id="stale-note" class="stale"></p><div id="timeline">{"".join(timeline)}</div>' + follow_html()
    write(out_dir, "index.html", page("Agent-Ticker · daily changes at AI coding agents", body, "home"))

    archive_items = []
    for d in days:
        b = briefs.get(d)
        n = len([e for e in by_day.get(d, [])])
        if b or n:
            day_body = (brief_html(d, b) if b else f"<h1>{nice_date(d)}</h1>") + "".join(entry_html(e) for e in by_day.get(d, []))
            new_that_day = [e for e in entries if e.get("first_seen") == d and e["published"] != d]
            if new_that_day and b and b.get("count"):
                day_body += "<h4>Also spotted today</h4>" + "".join(entry_html(e) for e in new_that_day[:20])
            label = b["headline"] if b else f"{n} change{'s' if n != 1 else ''} published"
            write(out_dir, f"day-{d}.html", page(f"Agent-Ticker · {nice_date(d)}", day_body, "archive", label))
            archive_items.append(f'<li><a href="day-{d}.html"><time>{d}</time> {E_(label)}</a></li>')
    write(out_dir, "archive.html", page("Agent-Ticker · Archive", f'<h1>Archive</h1><p class="muted">Every day with an official change. Days without a release are skipped; history starts with the 30 days loaded at launch.</p><ul class="archive">{"".join(archive_items[:400])}</ul>', "archive"))

    rows = []
    for k, v in AGENTS.items():
        p = plans.get(k)
        last_price = next((e for e in entries if e["agent"] == k and e.get("category") == "pricing"), None)
        plan_rows = "".join(f"<tr><td>{E_(x['plan'])}</td><td><b>{E_(x['price'])}</b></td><td>{E_(x['note'])}</td></tr>" for x in (p or {}).get("plans", []))
        rows.append(
            f"""<section class="pricebox a-border-{k}"><h3><span class="agent a-{k}">{E_(v['name'])}</span></h3>
<p class="muted">Checked {E_((p or {}).get('checked', 'daily'))} · <a href="{E_(PRICING_PAGES[k])}">official pricing page</a>
{(' · last change: ' + nice_date(last_price['published'])) if last_price else ''}</p>
{'<p class="muted">The pricing page changed; this summary is being refreshed.</p>' if (p or {}).get('stale') else ''}
{f'<table>{plan_rows}</table>' if plan_rows else '<p class="muted">The plan table is filled in by the AI editor; until then, open the official pricing page.</p>'}</section>"""
        )
    write(out_dir, "pricing.html", page("Agent-Ticker · Pricing watch", "<h1>Pricing watch</h1><p>Every morning the ticker re-reads each official pricing page, compares it with yesterday and flags any price or plan line that changed.</p>" + "".join(rows), "pricing"))

    write(out_dir, "autonomy.html", page("Agent-Ticker · How it runs itself", autonomy_html(runs, entries), "autonomy"))
    write(out_dir, "feed.xml", rss(entries, briefs))
    write(out_dir, "data.json", json.dumps({"generated": datetime.now(timezone.utc).isoformat(), "entries": entries[:300], "briefs": briefs, "plans": plans}, ensure_ascii=False))
    write(out_dir, ".nojekyll", "")
    return out_dir


def autonomy_html(runs, entries):
    total_runs = len(runs)
    human = sum(r.get("human_edits", 0) for r in runs)
    ai_items = sum(1 for e in entries if e.get("editor") == "ai")
    rows = []
    for r in reversed(runs[-60:]):
        ok = sum(1 for s in r["sources"].values() if s.get("ok"))
        rows.append(
            f"<tr><td>{r['date']}</td><td>{ok}/{len(r['sources'])}</td><td>{r.get('new', 0)}</td><td>{r.get('pricing_changes', 0)}</td>"
            f"<td>{r.get('ai_calls', 0)}</td><td>{r.get('seconds', '')}s</td><td>{r.get('human_edits', 0)}</td></tr>"
        )
    steps = [
        ("05:30 UTC", "A scheduled GitHub Actions job wakes up. No server, no human."),
        ("Collect", "It reads the official changelogs: Devin release notes, Claude Code and Codex GitHub releases, Cursor's changelog feed and xAI's release notes."),
        ("Watch prices", "It re-reads each official pricing page and diffs the price and plan lines against yesterday's snapshot."),
        ("Edit", "An AI editor (Google Gemini, on its free tier) tags every new item as feature, model, pricing, removal or fix, writes a one-line takeaway and the daily brief. If the AI is unavailable, rule-based editing takes over so the site never stalls."),
        ("Publish", "It rebuilds this site, the RSS feed and the JSON API, commits the data and deploys to GitHub Pages."),
        ("Report", "Every run is logged below, including source failures and human edits."),
    ]
    step_html = "".join(f"<li><b>{E_(a)}</b> {E_(b)}</li>" for a, b in steps)
    return f"""<h1>How Agent-Ticker runs itself</h1>
<div class="stats"><div><b>{total_runs}</b><span>daily runs</span></div><div><b>{len(entries)}</b><span>changes tracked</span></div>
<div><b>{ai_items}</b><span>items written by AI</span></div><div><b>{human}</b><span>human edits</span></div></div>
<ol class="steps">{step_html}</ol><p>Only official, publicly offered sources are read, and each site's robots.txt is respected. The human only steers: which agents to track and what the site looks like.</p>
<h2>Run log</h2><table class="log"><tr><th>Date</th><th>Sources OK</th><th>New items</th><th>Price changes</th><th>AI calls</th><th>Runtime</th><th>Human edits</th></tr>{''.join(rows)}</table>"""


def rss(entries, briefs):
    """Daily briefs plus the latest individual changes, newest first."""
    items = []
    for d in sorted(briefs, reverse=True)[:30]:
        b = briefs[d]
        desc = "<ul>" + "".join(f"<li>{E_(x)}</li>" for x in b.get("bullets", [])) + "</ul>"
        items.append((d + "T06:30:00", f"Brief · {nice_date(d)}: {b['headline']}", f"{SITE_URL}/day-{d}.html", desc))
    for e in entries[:50]:
        title = f"{AGENTS[e['agent']]['name']}: {e.get('headline') or e['title']}"
        items.append((e["published"] + "T06:00:00", title, entry_link(e), e.get("takeaway") or ""))
    out = []
    for when, title, link, desc in sorted(items, reverse=True):
        pub = format_datetime(datetime.fromisoformat(when + "+00:00"))
        out.append(
            f"<item><title>{E_(title)}</title><link>{E_(link)}</link><guid isPermaLink=\"false\">{E_(link)}|{E_(title)}</guid>"
            f"<pubDate>{pub}</pubDate><description>{E_(desc)}</description></item>"
        )
    items = out
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Agent-Ticker</title><link>{SITE_URL}/</link>
<description>Daily changes at Devin, Claude Code, Codex, Cursor and Grok, from official sources.</description><language>en</language>
{''.join(items)}</channel></rss>
"""


def write(out_dir, name, content):
    with open(os.path.join(out_dir, name), "w") as f:
        f.write(content)
