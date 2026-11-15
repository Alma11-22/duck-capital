# Rebound AI

Finds stocks that sold off on bad news and scores how likely they are to recover.
It also flags bad news **before** a stock drops. Both scanners run at the same time, every weekday.

## What it does each day

1. **Prices for every US stock.** One call to Massive (formerly Polygon) gets the whole market's closing prices.
2. **Two scanners, side by side:**
   - **Drop scanner.** Stocks down 10%+ from their 30-day high, $5+ share price, $5M+ traded a day, and $2B+ market cap.
   - **Early warning.** Your watchlist plus the 100 most-traded stocks. Reads the last 3 days of news and SEC filings, and alerts when there's bad news but the stock hasn't dropped 10% yet.
3. **Checks on each drop:** what kind of news it was (bad press, short report, AI fear, macro/policy, business miss), insider buying or selling, analyst upgrades or downgrades, debt, cash, revenue trend, and SEC red-flag filings (CEO/CFO exits, restatements, auditor changes, cyber incidents).
4. **Score (0–100).** It starts from how often that kind of selloff recovered across the 100 past cases in `data/library.csv`, then adjusts for the checks above. Each score comes with the most similar past cases, staged buy levels, and what would break the thesis.
5. **Claude review (optional).** The top 15 names get a "temporary scare or real damage?" verdict, which moves the score by up to ±15.
6. **Paper portfolio.** Anything scoring 65+ is logged in `data/paper_portfolio.csv` and tracked daily, so the hit rate is measured, not guessed.

Output: `reports/latest.html` (phone-friendly), plus daily CSVs.

## Free data sources

| What | Source | Key |
|---|---|---|
| All-market daily prices | Massive (Polygon) Basic, $0 | massive.com → sign up → API key |
| News, profile, fundamentals, analysts, insiders | Finnhub free, $0 | finnhub.io → sign up → API key |
| 8-K red flags, Form 4 insider filings | SEC EDGAR, $0 | none (just a contact email) |
| Judgment layer (optional) | Anthropic API, pay per use | console.anthropic.com |

The first run backfills about 25 trading days of prices, which takes about 5 minutes on the free plan. After that it's one price call a day.
The free plans only give the prior day's prices after midnight US Eastern time, which is why the schedule runs in the early morning.

## Try it now (no keys)

```
pip install -r requirements.txt
python run.py --demo
open reports/latest.html
```

## Run it for real

**On your computer:**
```
export MASSIVE_API_KEY=...  FINNHUB_API_KEY=...  SEC_CONTACT_EMAIL=you@example.com
# optional: export ANTHROPIC_API_KEY=...
python run.py
```

**Automatically every weekday (free, on GitHub):**
1. Put this folder in a private GitHub repo.
2. Settings → Secrets and variables → Actions: add `MASSIVE_API_KEY`, `FINNHUB_API_KEY`, `SEC_CONTACT_EMAIL` (and optionally `ANTHROPIC_API_KEY`).
3. Actions tab → daily-scan → Run workflow, to test it. After that it runs by itself at 06:30 UTC, Tuesday to Saturday.

## Tuning

Everything is in `config.yaml`: drop threshold, lookback window, size filters, watchlist, how many names get checked, paper-buy cutoff and buy tranches.

## Upgrading to paid data later

Each provider lives in `rebound/providers/` behind the same small interface. A paid source (FMP, Massive Starter, etc.) is a new file there; the scanners don't change.

## Limits to know

- Headline reading uses keyword rules, so it's crude. The Claude layer is what reads nuance.
- Some Finnhub free accounts can't access insider trades. The score skips that check when it's missing.
- The case library is 100 hand-picked famous selloffs with approximate prices. Every paper pick adds to the real track record.
- Not investment advice.
