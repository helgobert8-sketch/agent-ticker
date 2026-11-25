"""Render the baseline as HTML, with evidence reused by the browser-only stack check."""
import json
from html import escape as esc

VENDORS = {
    "claude": ("Claude", "claude-code"),
    "chatgpt": ("ChatGPT", "codex"),
    "grok": ("Grok / X", "grok"),
    "devin": ("Devin", "devin"),
    "gemini": ("Google / Gemini", "gemini"),
}
LABELS = {
    "price_plans": "Price & plans",
    "billing_model": "Billing model",
    "usage_limits": "Usage limits",
    "top_model_access": "Top model access",
    "coding_agent": "Coding agent",
    "always_on_agent": "Always-on agent",
}
GROK_CURRENT = ("The X Subscription Plus", "The X Subscription Premium", "The X Subscription Super", "The X Subscription Ultra")
GROK_ROUTINES = (*GROK_CURRENT[1:], "SuperGrok", "SuperGrok Plus", "SuperGrok Heavy", "X Premium+")
GROK_TIER_EVIDENCE = {
    "price_plans": dict.fromkeys(GROK_CURRENT, "conditional"),
    "billing_model": {**dict.fromkeys(GROK_CURRENT, "verified"), "SuperGrok": "conditional"},
    "usage_limits": dict.fromkeys((*GROK_CURRENT, "SuperGrok"), "conditional"),
    "top_model_access": dict.fromkeys(GROK_CURRENT[1:], "conditional"),
    "coding_agent": dict.fromkeys(GROK_CURRENT, "conditional"),
    "always_on_agent": {**dict.fromkeys(GROK_ROUTINES, "conditional"),
                        GROK_CURRENT[0]: "not included", "SuperGrok Lite": "not included"},
}


def plan_label(vendor, tier):
    return tier if vendor in ("grok", "gemini") else f"{VENDORS[vendor][0]} {tier}"


def tier_evidence(row, vendor, status, tiers):
    if vendor == "grok" and status in ("verified", "conditional"):
        evidence = GROK_TIER_EVIDENCE.get(row, {})
        return {tier: evidence.get(tier, "not checked") for names in tiers.values() for tier in names}
    names = (name for group in tiers.values() for name in group) if isinstance(tiers, dict) else tiers
    return {plan_label(vendor, tier): status for tier in names}


def cell_html(vendor, cell, source, update, evidence):
    name, color = VENDORS[vendor]
    changed = source.get("changed", "") >= cell["checked"]
    update = update if update.get("date", "") >= cell["checked"] else None
    verified = cell["status"] == "verified" and not changed and not update
    flags = []
    if update:
        link = esc(f'day-{update["published"]}.html#item-{update["id"]}')
        flags.append(f'<a class="map-flag" href="{link}" title="{esc(update["title"])}">New update, check</a>')
    if changed:
        flags.append(f'<span class="map-flag">Source changed, check <time>{esc(source["changed"])}</time></span>')
    if "error" in source:
        flags.append('<span class="map-flag">Source scan unavailable</span>')
    primary = cell["source_url"]
    extra = "".join(f'<li><a href="{esc(url)}">{esc(url.split("/")[2])} · source {i}</a></li>'
                    for i, url in enumerate(dict.fromkeys(cell.get("source_urls", [])), start=2) if url != primary)
    notes = "".join(f'<p>{label}{esc(cell[key])}</p>' for key, label in (("note", ""), ("eu_note", "EU: ")) if cell.get(key))
    if extra:
        notes += f'<ul>{extra}</ul>'
    details = f'<details><summary>Notes &amp; sources</summary>{notes}</details>' if notes else ""
    scan = f'<small>Source scan <time>{esc(source["checked"])}</time></small>' if source.get("checked") else ''
    return f"""<article class="map-cell" data-vendor="{vendor}" data-status="{esc(cell['status'])}" data-verified="{str(verified).lower()}" data-tier-evidence="{esc(json.dumps(evidence))}">
<h3 class="a-{color}">{name}</h3><span class="map-status">{esc(cell['status'].capitalize())}</span>
{''.join(flags)}<p>{esc(cell['value'])}</p><small><a href="{esc(primary)}">Official source</a> · checked <time>{esc(cell['checked'])}</time></small>
{scan}{details}</article>"""


def plan_groups(meta):
    groups = []
    for vendor in meta["vendors"]:
        label, color = VENDORS[vendor]
        tiers = meta["tiers"][vendor]
        groups.append(f'<details class="plan-group"><summary class="a-{color}">{label}</summary>')
        for group, names in (tiers.items() if isinstance(tiers, dict) else [("current", tiers)]):
            for name in names:
                plan = plan_label(vendor, name)
                tag = " <small>(legacy)</small>" if group == "legacy" else ""
                groups.append(f'<label><input type="checkbox" data-plan data-vendor="{vendor}" value="{esc(plan)}" autocomplete="off"> {esc(name)}{tag}</label>')
        groups.append("</details>")
    return "".join(groups)


def render(baseline, state):
    if not baseline:
        return "<h1>Subscription map</h1><p>The baseline is not available in this build.</p>"
    meta = baseline["meta"]
    rows = []
    row_links = []
    priorities = []
    for row, cells in baseline["rows"].items():
        label = LABELS[row]
        row_links.append(f'<a class="chip" href="#{row}">{label}</a>')
        priorities.append(f'<label><input type="checkbox" data-priority="{row}" autocomplete="off"> {label}</label>')
        cards = "".join(cell_html(vendor, cells[vendor], state.get("sources", {}).get(cells[vendor]["source_url"], {}),
                                  state.get("updates", {}).get(row, {}).get(vendor, {}),
                                  tier_evidence(row, vendor, cells[vendor]["status"], meta["tiers"][vendor]))
                        for vendor in meta["vendors"])
        rows.append(f'<section class="map-row" id="{row}" data-label="{label}"><h2>{label}</h2><div class="map-grid">{cards}</div></section>')
    definitions = "".join(f'<li><b>{esc(status.capitalize())}:</b> {esc(text)}</li>' for status, text in meta["status_definitions"].items())
    return f"""<section class="hero map-hero"><div class="kicker">5 vendors · 6 rows · official sources</div>
<h1>Subscription map</h1><p>Compare what individual paid AI subscriptions include, from price and limits to coding and scheduled agents.</p>
<a class="btn" href="#stack-check">Check my stack</a></section>
<section class="map-guide"><p>{esc(meta['scope'])}</p>
<details><summary>What is checked and what is automated?</summary>
<p>The baseline was checked on <time>{esc(meta['checked'])}</time>. Always-on means a plan can start scheduled work without an open user session.
No EU note is not a guarantee of availability.</p><ul>{definitions}</ul>
<p>Daily runs look for related new ticker items using keywords where the ticker covers the vendor. They also compare readable text from each cell’s primary source against the last successful scan, without AI. A first scan only sets a comparison point; an unavailable scan is reported separately.</p>
<p>Flags are review prompts: the page or topic may have changed without any plan entitlement changing. Automation never updates a cell’s claim, evidence status or editorial check date.</p></details></section>
<div class="map-jumps">{"".join(row_links)}</div>
{''.join(rows)}
<section class="stack-check" id="stack-check"><div class="kicker">Private comparison</div><h2>Stack check</h2>
<p>Pick the subscriptions you pay for. No account: your choices stay on this page and are not sent or saved.</p>
<div id="stack-controls" hidden>
<fieldset><legend>Your paid plans</legend><div class="plan-groups">{plan_groups(meta)}</div></fieldset>
<fieldset><legend>Matters to me <small id="priority-count" aria-live="polite">0 of 3</small></legend>
<p class="muted">Optional: mark up to three rows to put them first in the gap view.</p><div class="map-priorities">{"".join(priorities)}</div></fieldset>
<p class="muted">The “both offer” count includes only verified, unflagged coverage. A row counts once when two or more picked plans meet that bar; it doesn’t mean they offer the same thing. Conditional coverage is shown separately and may depend on tier, region or rollout.</p>
<p id="stack-summary" role="status"></p><div id="stack-results" hidden>
<details open><summary>What your plans cover</summary><div id="stack-owned"></div></details>
<section><h3>Where your stack has no documented coverage</h3><p class="muted">Only rows with neither verified nor conditional coverage in your picked plans. Other plans are shown for comparison, not as recommendations.</p><div id="stack-gaps"></div></section>
</div></div><noscript>Enable JavaScript to compare your plans locally.</noscript></section>
<script src="subscriptions.js" defer></script>"""
