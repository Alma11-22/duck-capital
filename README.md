# 🦆 Duck Capital

Event-driven stock scanner. When something big happens (a pandemic, a war, tariffs, a rate shock, a bank scare, an AI breakthrough), it finds:

- **Who wins:** the obvious beneficiaries and the less obvious second-order ones (the "Zoom in 2020" trade).
- **Who overreacted:** good companies sold off harder than their numbers justify (the "airlines that came back" trade).

It also flags bad news **before** a stock drops, and checks whether each move is driven by the company's financials or by market psychology.

## What it does each weekday

1. **Prices for every US stock.** One call to Massive (formerly Polygon).
2. **Three scans run at the same time:**
   - **Event radar.** Reads market-wide headlines and matches them to the playbooks in `data/event_playbooks.yaml`. It then checks the market agrees: the playbook's losers falling while its winners hold up.
   - **Drop scanner.** Stocks down 10%+ from their 30-day high ($5+ share price, $5M+ traded a day, $2B+ market cap).
   - **Early warning.** Your watchlist plus the 100 most-traded stocks: bad news or SEC red-flag filings, but no big drop yet.
3. **Event winners.** For each live event: direct and second-order winners, scored on whether the market agrees yet, whether the stock is already up too much ("late"), and its financials. Each comes with a "sell when" signal for when the event's effect fades.
4. **Psychology vs. fundamentals.** For every stock it reads the financials (revenue and earnings growth, profit margin against its 5-year average, the last 4 earnings beats or misses, debt) and compares them with the price move.
   - A big drop with healthy numbers scores as **mostly psychology**, a buying opportunity.
   - A big jump with weak numbers scores as **mostly hype**, a warning.
5. **Rebound score (0–100).** It starts from how often that kind of selloff recovered across 100 past cases in `data/library.csv`, then adjusts for insiders, analysts, debt, SEC red flags, the psychology score, and whether the drop is part of a live event.
6. **Claude (optional).** A "temporary or real damage?" verdict on the top 15 rebound names, plus extra second-order winners for each live event.
7. **Paper portfolio.** Every high-scoring pick is tracked, so the hit rate of each strategy (rebounds vs. event winners) is measured, not guessed.

**Output:** a web page (GitHub Pages), an optional morning email, and CSVs in `reports/`.

## Free data sources

| What | Source | Key |
|---|---|---|
| All-market daily prices | Massive (Polygon) Basic, $0 | massive.com |
| News, financials, earnings, analysts, insiders | Finnhub free, $0 | finnhub.io |
| 8-K red flags, Form 4 insider filings | SEC EDGAR, $0 | none (just a contact email) |
| Judgment layer (optional) | Anthropic API, pay per use | console.anthropic.com |

## Setup (GitHub, runs by itself)

Settings → Secrets and variables → Actions → add `MASSIVE_API_KEY`, `FINNHUB_API_KEY` and `SEC_CONTACT_EMAIL`.

Optional secrets:
- `ANTHROPIC_API_KEY`, for the Claude layer.
- `EMAIL_TO`, `SMTP_USER`, `SMTP_PASSWORD` (a Gmail app password), for the morning email.

Then go to Actions → daily-scan → Run workflow. After that it runs at 06:30 UTC, Tuesday to Saturday.

## Try it locally

```
pip install -r requirements.txt
python run.py --demo     # fake market in the middle of a tariff shock, no keys needed
```

## Tuning

- `config.yaml`: thresholds, watchlist, event sensitivity, paper-buy cutoffs.
- `data/event_playbooks.yaml`: add events, keywords, and winner/loser tickers.

## Limits

- Event and headline detection uses keyword rules. The Claude layer is what reads nuance.
- The playbooks are hand-built from past events. Every new event teaches you what to add.
- The case library is 100 famous selloffs with approximate prices.
- Not investment advice.
