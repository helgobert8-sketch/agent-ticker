# Agent-Ticker

What changed today at **Devin, Claude Code, Codex, Cursor and Grok**: features, models and pricing, in one daily briefing for vibe coders.

Live: https://helgobert8-sketch.github.io/agent-ticker/

## How it runs itself

A GitHub Actions cron (`.github/workflows/daily.yml`, 05:30 UTC) does the daily work with no human in the loop:

1. **Collect** official sources only: release notes, RSS/Atom feeds, GitHub releases and pricing pages (see `ticker/sources.py`).
2. **Dedupe** against everything seen before (`data/entries.json`, `data/seen.json`).
3. **Edit** with an LLM (any OpenAI-compatible API, OpenAI by default): category, headline, one-line takeaway, and the daily brief. Without a token or on quota errors it falls back to rules, so the ticker never stalls.
4. **Watch pricing**: normalized snapshots in `data/pricing/` are diffed daily; price lines that move become a pricing item.
5. **Publish** a static site, RSS (`feed.xml`) and JSON (`data.json`) to GitHub Pages, and commit the data back.

Every run is logged on the site's *Autonomy* page.

## Configuration

| Name | Kind | Default |
| --- | --- | --- |
| `AI_TOKEN` | secret | unset: rule-based editing only |
| `AI_BASE_URL` | variable | `https://api.openai.com/v1` (any OpenAI-compatible endpoint) |
| `AI_MODEL` | variable | `gpt-4.1-mini` |
| `AI_MAX_CALLS` | env | `12` per run |

## Local run

```
python -m ticker.run --data-dir data --out-dir public
python -m unittest discover -s tests
```

No dependencies beyond the Python 3.10+ standard library.

Not affiliated with Cognition, Anthropic, OpenAI, Anysphere or xAI; every item links to its official source.
