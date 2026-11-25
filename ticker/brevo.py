"""Brevo newsletter sending for the daily brief.

The sender is deliberately separate from the AI editor: it only reads the
published brief, creates one deterministic Brevo campaign per UTC day and
sends it. Every Brevo failure is reported in the result instead of raising,
so a newsletter outage can never fail the ticker run.
"""
import html
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

from .util import load_json, now_iso, save_json

API_URL = "https://api.brevo.com/v3"
CAMPAIGN_TAG = "agent-ticker-daily"
STATE_FILE = "newsletter.json"
# Public in this repository's commit authors; also the default sender of the owner's Brevo account.
FALLBACK_SENDER = {"email": "helgobert8@gmail.com", "name": "Agent-Ticker"}
E_ = html.escape


class BrevoError(Exception):
    pass


def api(key, method, path, payload=None, timeout=20):
    body = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        API_URL + path,
        data=body,
        method=method,
        headers={"api-key": key, "accept": "application/json", "content-type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")[:500]
        try:
            detail = json.loads(raw)
            msg = detail.get("message") or raw
            code = detail.get("code")
        except json.JSONDecodeError:
            msg, code = raw or exc.reason, None
        raise BrevoError(f"HTTP {exc.code} {code or ''}: {msg}".strip()) from None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise BrevoError(f"{type(exc).__name__}: {exc}") from None


def campaign_name(day):
    return f"Agent-Ticker daily brief {day}"


def campaign_html(day, brief, site_url):
    bullets = "".join(f'<li style="margin:0 0 12px">{E_(b)}</li>' for b in brief.get("bullets", []))
    count = brief.get("count") or len(brief.get("bullets", []))
    day_url = f"{site_url}/day-{day}.html"
    return f"""<!doctype html>
<html><body style="margin:0;padding:0;background:#f6f4ef;font-family:Arial,Helvetica,sans-serif;color:#1e1e1e">
<div style="max-width:640px;margin:0 auto;padding:28px 18px">
  <div style="background:#ffffff;border:1px solid #e5e0d5;border-radius:14px;padding:28px">
    <p style="margin:0 0 10px;color:#746c5c;font-size:13px;letter-spacing:.08em;text-transform:uppercase">Agent-Ticker daily brief · {E_(day)}</p>
    <h1 style="margin:0 0 18px;font-size:24px;line-height:1.25">{E_(brief['headline'])}</h1>
    <ul style="margin:0 0 22px;padding-left:22px;font-size:16px;line-height:1.45">{bullets}</ul>
    <p style="margin:0 0 22px"><a style="display:inline-block;background:#1f5eff;color:#ffffff;text-decoration:none;border-radius:8px;padding:11px 16px;font-weight:bold" href="{E_(day_url)}">Read all {count} changes</a></p>
    <p style="margin:0;color:#746c5c;font-size:13px">Official changelogs, release notes and pricing pages for Devin, Claude Code, Codex, Cursor and Grok.</p>
  </div>
  <p style="margin:18px 0 0;color:#8a8172;font-size:12px;line-height:1.5;text-align:center">
    <a href="{E_(site_url)}/" style="color:#665f51">Agent-Ticker</a> ·
    <a href="{{{{ unsubscribe }}}}" style="color:#665f51">Unsubscribe</a>
  </p>
</div>
</body></html>"""


def configured_list_id():
    try:
        return int(os.environ.get("BREVO_LIST_ID") or 0) or None
    except ValueError:
        raise BrevoError("BREVO_LIST_ID must be a number")


def contact_lists(key):
    out, offset = [], 0
    while offset < 1000:
        query = urllib.parse.urlencode({"limit": 50, "offset": offset, "sort": "desc"})
        data = api(key, "GET", "/contacts/lists?" + query)
        batch = data.get("lists") or []
        out.extend(batch)
        count = data.get("count")
        if len(batch) < 50 or (count and len(out) >= count):
            return out
        offset += 50
    raise BrevoError("too many Brevo contact lists to scan safely")


def choose_list(key, state):
    wanted = configured_list_id()
    lists = contact_lists(key)
    if wanted:
        found = next((x for x in lists if x.get("id") == wanted), None)
        if not found:
            raise BrevoError(f"configured BREVO_LIST_ID {wanted} was not found")
        return found
    name_wanted = (os.environ.get("BREVO_LIST_NAME") or "").strip().lower()
    if name_wanted:
        found = next((x for x in lists if (x.get("name") or "").lower() == name_wanted), None)
        if found:
            return found
        raise BrevoError(f"configured BREVO_LIST_NAME {name_wanted!r} was not found")
    saved = (state.get("list") or {}).get("id")
    if saved:
        found = next((x for x in lists if x.get("id") == saved), None)
        if found:
            return found
    def normalized(x):
        return re.sub(r"[^a-z0-9]", "", (x.get("name") or "").lower())

    matches = [x for x in lists if "agentticker" in normalized(x)]
    if len(matches) == 1:
        return matches[0]
    exact_daily = [x for x in matches if normalized(x) == "agenttickerdaily"]
    if len(exact_daily) == 1:
        return exact_daily[0]
    raise BrevoError("no unambiguous Agent-Ticker list found; set BREVO_LIST_ID or BREVO_LIST_NAME")


def list_contacts(key, list_id):
    contacts, offset = [], 0
    while offset < 5000:
        query = urllib.parse.urlencode({"limit": 500, "offset": offset, "sort": "desc"})
        data = api(key, "GET", f"/contacts/lists/{list_id}/contacts?" + query)
        batch = data.get("contacts") or []
        contacts.extend(batch)
        count = data.get("count")
        if len(batch) < 500 or (count and len(contacts) >= count):
            return contacts, count or len(contacts)
        offset += 500
    raise BrevoError("too many Brevo contacts to scan safely")


def deliverable_contact_count(contacts, list_id):
    return sum(
        1
        for contact in contacts
        if not contact.get("emailBlacklisted") and list_id not in (contact.get("listUnsubscribed") or [])
    )


def choose_sender(key, state):
    wanted_id = os.environ.get("BREVO_SENDER_ID")
    wanted_email = (os.environ.get("BREVO_SENDER_EMAIL") or "").strip().lower()
    if wanted_id:
        try:
            return {"id": int(wanted_id), "name": os.environ.get("BREVO_SENDER_NAME") or "Agent-Ticker"}
        except ValueError:
            raise BrevoError("BREVO_SENDER_ID must be a number")
    if wanted_email:
        return {"email": wanted_email, "name": os.environ.get("BREVO_SENDER_NAME") or "Agent-Ticker"}
    try:
        data = api(key, "GET", "/senders")
    except BrevoError:
        return dict(FALLBACK_SENDER)
    senders = data.get("senders") or []
    active = [x for x in senders if x.get("active")]
    saved = state.get("sender") or {}
    for sender in active:
        if wanted_id and str(sender.get("id")) == wanted_id:
            return sender
        if wanted_email and (sender.get("email") or "").lower() == wanted_email:
            return sender
        if not wanted_id and not wanted_email and saved.get("id") == sender.get("id"):
            return sender
    if wanted_id or wanted_email:
        raise BrevoError("configured Brevo sender was not found or is not active")
    for sender in active:
        name = (sender.get("name") or "").lower().replace("_", "-")
        if "agent" in name and "ticker" in name:
            return sender
    if active:
        return active[0]
    raise BrevoError("no active Brevo sender found")


def find_campaign(key, day):
    query = urllib.parse.urlencode({"limit": 20, "sort": "desc", "excludeHtmlContent": "true"})
    data = api(key, "GET", "/emailCampaigns?" + query)
    name = campaign_name(day)
    for c in data.get("campaigns") or []:
        if c.get("name") == name:
            return c
    return None


def report_campaign(key, campaign_id):
    query = urllib.parse.urlencode({"statistics": "globalStats", "excludeHtmlContent": "true"})
    return api(key, "GET", f"/emailCampaigns/{campaign_id}?" + query)


def recipient_count(report):
    stats = ((report or {}).get("statistics") or {}).get("globalStats") or {}
    return stats.get("sent")


def compact_report(report):
    if not report:
        return {}
    return {
        "id": report.get("id"),
        "name": report.get("name"),
        "status": report.get("status"),
        "recipients": recipient_count(report),
        "sentDate": report.get("sentDate"),
        "listIds": ((report.get("recipients") or {}).get("lists") or []),
    }


def operation_report(kind, report):
    compact = compact_report(report)
    campaign_status = compact.pop("status", None)
    return {"status": kind, "campaign_status": campaign_status, **compact}


def save_state(data_dir, state):
    save_json(os.path.join(data_dir, STATE_FILE), state)


def send_daily_brief(data_dir="data", day=None, site_url="https://helgobert8-sketch.github.io/agent-ticker", key=None):
    """Send today's brief once. Returns a JSON-safe result and never raises for Brevo/API failures."""
    day = day or now_iso()[:10]
    key = key if key is not None else os.environ.get("BREVO_API_KEY", "")
    if not key:
        return {"status": "skipped", "reason": "BREVO_API_KEY is not set", "date": day}
    briefs = load_json(os.path.join(data_dir, "briefs.json"), {})
    brief = briefs.get(day)
    if not brief:
        return {"status": "skipped", "reason": "no brief for this date", "date": day}

    state = load_json(os.path.join(data_dir, STATE_FILE), {})
    campaigns = state.setdefault("campaigns", {})
    prior = campaigns.get(day) or {}
    name = campaign_name(day)
    try:
        if prior.get("id") and prior.get("status") not in (None, "draft", "error"):
            report = report_campaign(key, prior["id"])
            campaigns[day] = {**prior, **compact_report(report), "checked": now_iso(), "deduped": True}
            save_state(data_dir, state)
            return {"reason": "campaign already exists", **operation_report("skipped", report), "date": day}

        existing = find_campaign(key, day)
        cid = prior.get("id") or (existing or {}).get("id")
        existing_status = (existing or {}).get("status") or prior.get("status")
        if cid and existing_status not in (None, "draft", "error"):
            report = report_campaign(key, cid)
            campaigns[day] = {**prior, **compact_report(report), "checked": now_iso(), "deduped": True}
            save_state(data_dir, state)
            return {"reason": "campaign already exists", **operation_report("skipped", report), "date": day}

        if not cid:
            contact_list = choose_list(key, state)
            sender = choose_sender(key, state)
            state["list"] = {"id": contact_list.get("id"), "name": contact_list.get("name")}
            state["sender"] = {"id": sender.get("id"), "email": sender.get("email"), "name": sender.get("name")}
            subject = ("Agent-Ticker: " + brief["headline"])[:140]
            sender_payload = {"id": sender["id"]} if sender.get("id") else {"email": sender["email"], "name": sender.get("name") or "Agent-Ticker"}
            payload = {
                "name": name,
                "subject": subject,
                "previewText": (brief.get("bullets") or ["What changed in your AI coding agents today"])[0][:140],
                "sender": sender_payload,
                "recipients": {"listIds": [contact_list["id"]]},
                "htmlContent": campaign_html(day, brief, site_url.rstrip("/")),
                "tag": CAMPAIGN_TAG,
                "mirrorActive": True,
            }
            created = api(key, "POST", "/emailCampaigns", payload)
            cid = created.get("id")
            if not cid:
                raise BrevoError("campaign creation returned no id")
            campaigns[day] = {"id": cid, "name": name, "status": "draft", "created": now_iso(), "listIds": [contact_list["id"]]}
            save_state(data_dir, state)
        else:
            campaigns.setdefault(day, {**prior, "id": cid, "name": name})

        api(key, "POST", f"/emailCampaigns/{cid}/sendNow")
        campaigns[day].update({"id": cid, "name": name, "sendRequested": now_iso(), "status": "queued"})
        save_state(data_dir, state)
        report = report_campaign(key, cid)
        campaigns[day].update(compact_report(report))
        campaigns[day]["checked"] = now_iso()
        save_state(data_dir, state)
        return {**operation_report("sent", report), "date": day}
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"[:300]
        current = campaigns.get(day) or prior
        campaigns[day] = {**current, "name": name, "status": current.get("status") or "error", "error": error, "checked": now_iso()}
        save_state(data_dir, state)
        return {"status": "error", "error": error, "date": day, "id": current.get("id")}


def list_status(data_dir="data", key=None):
    key = key if key is not None else os.environ.get("BREVO_API_KEY", "")
    if not key:
        return {"status": "error", "error": "BREVO_API_KEY is not set"}
    state = load_json(os.path.join(data_dir, STATE_FILE), {})
    try:
        contact_list = choose_list(key, state)
        contacts, total = list_contacts(key, contact_list["id"])
        return {
            "status": "ok",
            "listId": contact_list.get("id"),
            "listName": contact_list.get("name"),
            "contacts": total,
            "deliverableContacts": deliverable_contact_count(contacts, contact_list["id"]),
        }
    except Exception as exc:
        return {"status": "error", "error": f"{type(exc).__name__}: {exc}"[:300]}


def verify_daily_brief(data_dir="data", day=None, key=None):
    day = day or now_iso()[:10]
    key = key if key is not None else os.environ.get("BREVO_API_KEY", "")
    if not key:
        return {"status": "error", "error": "BREVO_API_KEY is not set", "date": day}
    state = load_json(os.path.join(data_dir, STATE_FILE), {})
    prior = (state.get("campaigns") or {}).get(day) or {}
    try:
        cid = prior.get("id") or (find_campaign(key, day) or {}).get("id")
        if not cid:
            return {"status": "missing", "date": day}
        raw = report_campaign(key, cid)
        prior.update(compact_report(raw))
        prior["checked"] = now_iso()
        state.setdefault("campaigns", {})[day] = prior
        save_state(data_dir, state)
        return {**operation_report("ok", raw), "date": day}
    except Exception as exc:
        return {"status": "error", "error": f"{type(exc).__name__}: {exc}"[:300], "date": day, "id": prior.get("id")}


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--day")
    group = ap.add_mutually_exclusive_group()
    group.add_argument("--send", action="store_true")
    group.add_argument("--verify", action="store_true")
    group.add_argument("--list-status", action="store_true")
    args = ap.parse_args()
    if args.list_status:
        result = list_status(args.data_dir)
    else:
        fn = verify_daily_brief if args.verify else send_daily_brief
        result = fn(args.data_dir, args.day)
    print("newsletter:", json.dumps(result, sort_keys=True))
    # Newsletter delivery must never fail the ticker run, even when Brevo is down.


if __name__ == "__main__":
    main()
