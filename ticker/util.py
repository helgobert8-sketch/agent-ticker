import hashlib
import html
import json
import os
import re
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urlsplit

USER_AGENT = "AgentTicker/1.0 (+https://github.com/helgobert8-sketch/agent-ticker)"


ROBOTS_EXEMPT = {"api.github.com"}  # a documented REST API, not a crawled website
_robots_cache = {}


class RobotsDisallowed(Exception):
    pass


def _get(url, headers=None, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def fetch(url, headers=None, timeout=30):
    """GET a page, but only if the site's robots.txt allows it."""
    if not robots_allows(robots_rules(url), url):
        raise RobotsDisallowed(f"robots.txt disallows {url}")
    return _get(url, headers, timeout)


def robots_rules(url):
    parts = urlsplit(url)
    if parts.netloc in ROBOTS_EXEMPT:
        return []
    key = f"{parts.scheme}://{parts.netloc}"
    if key not in _robots_cache:
        try:
            _robots_cache[key] = parse_robots(_get(key + "/robots.txt", timeout=15))
        except urllib.error.HTTPError as exc:
            if exc.code >= 500:
                raise
            _robots_cache[key] = [(False, "/")] if exc.code in (401, 403) else []
    return _robots_cache[key]


def parse_robots(text, agent="agentticker"):
    """Return [(allow, path)] for our user agent, falling back to the '*' group."""
    groups, current, in_rules = [], None, False
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, val = (x.strip() for x in line.split(":", 1))
        key = key.lower()
        if key == "user-agent":
            if current is None or in_rules:
                current, in_rules = {"agents": [], "rules": []}, False
                groups.append(current)
            current["agents"].append(val.lower())
        elif key in ("allow", "disallow") and current is not None:
            in_rules = True
            if val:
                current["rules"].append((key == "allow", val))
    mine = [g for g in groups if any(a != "*" and a in agent for a in g["agents"])]
    return [r for g in (mine or [g for g in groups if "*" in g["agents"]]) for r in g["rules"]]


def robots_allows(rules, url):
    """Longest matching rule wins, Allow wins ties; supports * and $ like Google and GitHub use."""
    parts = urlsplit(url)
    path = (parts.path or "/") + (f"?{parts.query}" if parts.query else "")
    best = (-1, True)
    for allow, rule in rules:
        rx = re.escape(rule).replace(r"\*", ".*")
        if rx.endswith(r"\$"):
            rx = rx[:-2] + "$"
        if re.match(rx, path):
            best = max(best, (len(rule), allow))
    return best[1]


def github_headers():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    h = {"Accept": "application/vnd.github+json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def stable_id(*parts):
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:12]


def today():
    return datetime.now(timezone.utc).date().isoformat()


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class _TextExtractor(HTMLParser):
    BLOCK = {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "br", "section", "ul", "ol", "table"}
    SKIP = {"script", "style", "noscript", "svg", "head", "template"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")
        if tag == "li" and not self.skip:
            self.parts.append("- ")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def html_to_text(markup):
    p = _TextExtractor()
    p.feed(markup)
    text = "".join(p.parts)
    lines = [re.sub(r"[ \t\xa0]+", " ", line).strip() for line in text.splitlines()]
    out, blank = [], False
    for line in lines:
        if not line:
            if not blank and out:
                out.append("")
            blank = True
            continue
        out.append(line)
        blank = False
    return "\n".join(out).strip()


def md_structure(text):
    """Headings become 'Heading:' and list markers '•'; nothing else is touched."""
    text = re.sub(r"^#{1,6}\s+(.+?)\s*#*$", r"\1:", text, flags=re.M)
    return re.sub(r"^\s*[-*+]\s+", "• ", text, flags=re.M)


def md_to_text(md):
    md = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", md)
    md = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", md)
    md = re.sub(r"\\([\\`*_{}\[\]()#+\-.!|<>])", r"\1", md)
    md = re.sub(r"\*{1,3}|`+", "", md)
    md = re.sub(r"(?<![\w\\])_{1,3}(?=\S)|(?<=\S)_{1,3}(?!\w)", "", md)
    return html.unescape(md).strip()


def clip_lines(text, n):
    """Like clip, but keeps line breaks so list items stay separate."""
    text = "\n".join(re.sub(r"[ \t]+", " ", l).strip() for l in (text or "").splitlines() if l.strip())
    return text if len(text) <= n else text[: n - 1].rsplit(" ", 1)[0] + "…"


def clip(text, n):
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= n else text[: n - 1].rsplit(" ", 1)[0] + "…"


def parse_date(value):
    value = value.strip()
    for fmt in ("%B %d, %Y", "%a, %d %b %Y %H:%M:%S %Z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return None


def load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, data):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=1, ensure_ascii=False, sort_keys=False)
        f.write("\n")


def days_between(a, b):
    return (date.fromisoformat(b) - date.fromisoformat(a)).days
