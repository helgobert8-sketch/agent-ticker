"""Daily routine: collect -> dedupe -> AI edit -> pricing watch -> brief -> log -> build.

    python -m ticker.run                 # full daily run (network + AI if a token is set)
    python -m ticker.run --build-only    # rebuild the site from data/
"""
import argparse
import os
import time
import traceback
from datetime import date, timedelta

from . import pricing, site, sources
from .ai import Editor
from .util import days_between, load_json, now_iso, save_json, today

AGENT_NAMES = {k: v["name"] for k, v in sources.AGENTS.items()}


def merge(store, fresh, day, backfill_days, seen=None):
    """Add unseen entries; return the new ones. Old history is only taken on the first run.

    `seen` holds ids of items skipped as too old, so they never resurface as news later."""
    seen = set() if seen is None else seen
    known = {e["id"] for e in store} | seen
    first_run = not store and not seen
    cutoff = (date.fromisoformat(day) - timedelta(days=backfill_days)).isoformat()
    new = []
    for e in fresh:
        if e["id"] in known:
            continue
        if not e.get("published"):
            e["published"] = day
        if e.get("date_precision") == "month" and not first_run:
            e["published"], e["date_precision"] = day, "day"  # month-only sources: date by first sighting
        too_old = e["published"][:7] < cutoff[:7] if e.get("date_precision") == "month" else e["published"] < cutoff
        if (first_run and too_old) or (not first_run and days_between(e["published"], day) > 45):
            seen.add(e["id"])  # history before launch, or old items surfacing late, are not news
            known.add(e["id"])
            continue
        e["first_seen"] = day
        known.add(e["id"])
        new.append(e)
    return new


def run(data_dir="data", out_dir="public", backfill_days=30, agents=None, editor=None):
    started = time.time()
    day = today()
    editor = editor or Editor()
    store = load_json(os.path.join(data_dir, "entries.json"), [])
    briefs = load_json(os.path.join(data_dir, "briefs.json"), {})
    plans = load_json(os.path.join(data_dir, "plans.json"), {})
    runs = load_json(os.path.join(data_dir, "runs.json"), [])
    seen = set(load_json(os.path.join(data_dir, "seen.json"), []))
    trigger = os.environ.get("GITHUB_EVENT_NAME") or "local"
    log = {"date": day, "started": now_iso(), "trigger": trigger, "sources": {}, "pricing": {}, "new": 0}
    previous = runs[-1]["sources"] if runs else {}

    fresh = []
    for agent in agents or sources.AGENTS:
        try:
            got = sources.collect(agent, year_hint=int(day[:4]), month_hint=int(day[5:7]))
            fresh.extend(got)
            log["sources"][agent] = {"ok": True, "items": len(got)}
            before = previous.get(agent, {}).get("items") or 0
            if not got or len(got) < before / 2:
                log["sources"][agent]["warning"] = f"{len(got)} items, {before} on the previous run"
        except Exception as exc:
            log["sources"][agent] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"[:200]}

    new = merge(store, fresh, day, backfill_days, seen)
    editor.enrich(new, AGENT_NAMES)
    for e in new:
        e.pop("body_full", None)

    pricing_changes = []
    for agent in agents or sources.AGENTS:
        try:
            res = pricing.check(agent, data_dir)
            log["pricing"][agent] = {"ok": True, "changed": res["changed"]}
            if res["rebased"]:
                log["pricing"][agent]["rebased"] = True  # page cleanup changed: new baseline, no alert
            if res["changed"]:
                pricing_changes.append(res)
                store.append(pricing_entry(res, day, editor))
            if res["changed"] or res["first"] or res["rebased"] or agent not in plans or plans[agent].get("stale"):
                extracted = editor.summarize_pricing(AGENT_NAMES[agent], res["text"])
                if extracted:
                    plans[agent] = {"plans": extracted, "checked": day, "url": res["url"]}
                elif agent in plans:
                    plans[agent]["stale"] = True  # retried on the next run; the page says it is outdated
            if agent in plans:
                plans[agent]["checked"] = day
        except Exception as exc:
            log["pricing"][agent] = {"ok": False, "error": f"{type(exc).__name__}: {exc}"[:200]}

    store.extend(new)
    store.sort(key=lambda e: (e["published"], e.get("first_seen", "")), reverse=True)

    todays = [e for e in store if e.get("first_seen") == day and not e.get("pricing") and (e["published"] >= (date.fromisoformat(day) - timedelta(days=3)).isoformat())]
    todays_pricing = [e["pricing"] for e in store if e.get("first_seen") == day and e.get("pricing")]
    if day in briefs and not new and not pricing_changes and not (briefs[day].get("editor") == "rules" and editor.enabled and (todays or todays_pricing)):
        pass  # a rerun on the same day with nothing new keeps the published brief, unless AI can now rewrite it
    elif runs or todays or todays_pricing:  # first run backfills history; brief only real news
        briefs[day] = editor.brief(day, todays, todays_pricing, AGENT_NAMES)
        briefs[day]["count"] = len(todays) + len(todays_pricing)
    else:
        briefs[day] = {"headline": "Agent-Ticker went live and loaded the last 30 days of official changes.", "bullets": [], "editor": "rules", "count": 0}

    backlog_calls = int(os.environ.get("AI_BACKLOG_CALLS", "4"))
    if editor.enabled and backlog_calls > 0:
        for e in [e for e in store if e.get("editor") == "pricing-watch" and e.get("pricing")][:2]:
            note = editor.pricing_note(AGENT_NAMES[e["agent"]], e["pricing"]["added"], e["pricing"]["removed"])
            if note["editor"] == "ai":
                e.update(note)
        backlog = [e for e in store if e.get("editor") == "rules"][: backlog_calls * 8]
        before = {e["id"]: (e.get("category"), e.get("headline"), e.get("takeaway")) for e in backlog}
        editor.enrich(backlog, AGENT_NAMES)
        for e in backlog:  # a failed call must not overwrite earlier text with rule output of a different shape
            if e.get("editor") != "ai":
                e["category"], e["headline"], e["takeaway"] = before[e["id"]]
        log["ai_backlog"] = sum(1 for e in backlog if e.get("editor") == "ai")

    log.update(
        new=len(new),
        pricing_changes=len(pricing_changes),
        ai_calls=editor.calls,
        ai_errors=editor.errors[:5],
        ai_model=editor.model if editor.token else None,
        seconds=round(time.time() - started, 1),
    )
    runs.append(log)

    save_json(os.path.join(data_dir, "entries.json"), store)
    save_json(os.path.join(data_dir, "briefs.json"), briefs)
    save_json(os.path.join(data_dir, "plans.json"), plans)
    save_json(os.path.join(data_dir, "runs.json"), runs[-400:])
    save_json(os.path.join(data_dir, "seen.json"), sorted(seen))
    site.build(data_dir, out_dir)
    return log


def pricing_entry(res, day, editor):
    from .util import stable_id

    added = "; ".join(res["added"][:6])
    removed = "; ".join(res["removed"][:6])
    body = (f"Now on the page: {added}" if added else "") + (f"\nNo longer on the page: {removed}" if removed else "")
    note = editor.pricing_note(AGENT_NAMES[res["agent"]], res["added"], res["removed"])
    return {
        "id": stable_id(res["agent"], "pricing", day),
        "agent": res["agent"],
        "title": f"{AGENT_NAMES[res['agent']]} pricing page changed",
        "headline": note["headline"],
        "takeaway": note["takeaway"],
        "body": body.strip(),
        "url": res["url"],
        "published": day,
        "first_seen": day,
        "date_precision": "day",
        "category": "pricing",
        "source": res["url"],
        "editor": note["editor"],
        "pricing": {"agent": res["agent"], "added": res["added"][:8], "removed": res["removed"][:8]},
    }


def ran_on_schedule(data_dir, day):
    runs = load_json(os.path.join(data_dir, "runs.json"), [])
    after_reset = f"{day}T08:00"  # a backup slot GitHub starts after midnight must not use up the next day's run
    return any(r.get("date") == day and r.get("trigger") == "schedule" and r.get("started", "") >= after_reset for r in runs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--out-dir", default="public")
    ap.add_argument("--build-only", action="store_true")
    ap.add_argument("--backfill-days", type=int, default=30)
    ap.add_argument("--skip-if-ran-today", action="store_true", help="for the backup schedule slot")
    args = ap.parse_args()
    if args.skip_if_ran_today and ran_on_schedule(args.data_dir, today()):
        print("a scheduled run already finished today; rebuilding only")
        args.build_only = True
    if args.build_only:
        site.build(args.data_dir, args.out_dir)
        return
    try:
        log = run(args.data_dir, args.out_dir, args.backfill_days)
    except Exception:
        traceback.print_exc()
        raise
    print({k: log[k] for k in ("date", "new", "pricing_changes", "ai_calls", "seconds")})
    failed = [a for a, s in log["sources"].items() if not s["ok"]]
    if failed:
        print("source failures:", failed)


if __name__ == "__main__":
    main()
