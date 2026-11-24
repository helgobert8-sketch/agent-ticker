# Agent-Ticker

What changed today at **Devin, Claude Code, Codex, Cursor and Grok**: features, models and pricing, in one daily briefing for vibe coders.

Live: https://helgobert8-sketch.github.io/agent-ticker/

## How it runs itself

A GitHub Actions cron (`.github/workflows/daily.yml`, 05:30 UTC) does the daily work with no human in the loop:

1. **Collect** official sources only: release notes, RSS/Atom feeds, GitHub releases and pricing pages (see `ticker/sources.py`).
2. **Dedupe** against everything seen before (`data/entries.json`, `data/seen.json`).
3. **Edit** with an LLM (Google Gemini free tier by default, or any OpenAI-compatible API): category, headline, one-line takeaway, and the daily brief. Without a token or on quota errors it falls back to rules, so the ticker never stalls.
4. **Watch pricing**: normalized snapshots in `data/pricing/` are diffed daily; price lines that move become a pricing item.
5. **Publish** a static site, RSS (`feed.xml`) and JSON (`data.json`) to GitHub Pages, and commit the data back.

Every run is logged on the site's *Autonomy* page.

## Configuration

| Name | Kind | Default |
| --- | --- | --- |
| `AI_TOKEN` | secret | a Gemini API key (free tier); unset: rule-based editing only |
| `AI_BASE_URL` | variable | `https://generativelanguage.googleapis.com/v1beta/openai` (any OpenAI-compatible endpoint, e.g. `https://api.openai.com/v1`) |
| `AI_MODEL` | variable | `gemini-4-hydrogen` (e.g. `gpt-4.1-mini` for OpenAI) |

Rule-based editing is the fallback whenever the AI is missing or fails.
| `AI_MAX_CALLS` | env | `30` per run |
| `AI_BACKLOG_CALLS` | env | `10` per run: AI re-edits up to 80 older rule-written items a day |

## Local run

```
python -m ticker.run --data-dir data --out-dir public
python -m unittest discover -s tests
```

No dependencies beyond the Python 3.10+ standard library.

Not affiliated with Cognition, Anthropic, OpenAI, Anysphere or xAI; every item links to its official source.
