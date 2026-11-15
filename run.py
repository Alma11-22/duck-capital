"""Duck Capital - daily run.

    python run.py           # real data (needs MASSIVE_API_KEY and FINNHUB_API_KEY)
    python run.py --demo    # fake data, no keys needed

Scans run at the same time; results land in reports/latest.html.
"""
import argparse
import concurrent.futures as cf
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from duck import classify, claude, events, notify, report  # noqa: E402
from duck.fundamentals import psych_score  # noqa: E402
from duck.portfolio import Paper  # noqa: E402
from duck.prices import PriceStore  # noqa: E402
from duck.scanners import drop_scan, early_warning_scan  # noqa: E402
from duck.score import Library, score  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="run on fake data")
    args = ap.parse_args()
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    cfg = yaml.safe_load(open("config.yaml"))

    if args.demo:
        from duck.providers.mock import Mock
        prices = details = sec = Mock()
        db, paper_path = "data/demo_prices.db", "data/demo_paper_portfolio.csv"
        cfg["watchlist"] = ["DDD", "EEE"]
    else:
        from duck.providers.finnhub import Finnhub
        from duck.providers.massive import Massive
        from duck.providers.sec import SEC
        prices, details, sec = Massive(), Finnhub(), SEC()
        db, paper_path = "data/prices.db", "data/paper_portfolio.csv"

    print("1/6 Updating prices for all US stocks...")
    store = PriceStore(db)
    n = store.update(prices, cfg["lookback_days"])
    window, asof = store.window(cfg["lookback_days"])
    print(f"    fetched {n} new day(s); {len(window)} tickers as of {asof}")
    if not window:
        sys.exit("No price data yet. Check MASSIVE_API_KEY, or run after midnight US Eastern.")

    print("2/6 Running the scans at the same time (event radar, drops, early warnings)...")
    playbooks = events.load_playbooks()
    with cf.ThreadPoolExecutor(max_workers=3) as pool:
        f_evt = pool.submit(lambda: events.detect(details.market_news(cfg["event_news_days"]),
                                                  playbooks, store, cfg))
        f_drop = pool.submit(drop_scan, window, details, cfg)
        f_warn = pool.submit(early_warning_scan, window, details, sec, cfg, classify.negativity)
        live, drops, warnings = f_evt.result(), f_drop.result(), f_warn.result()

    print("3/6 Event winners...")
    for ev in live:
        known = set(playbooks[ev["key"]]["winners"]["direct"] + playbooks[ev["key"]]["winners"]["second_order"])
        ideas = claude.event_ideas(ev, known, cfg)
        ev["winners"] = events.rank_winners(ev, playbooks, store, details, cfg, extra=ideas)
        for w in ev["winners"]:
            p = psych_score(details.metrics(w["ticker"]), details.earnings_surprises(w["ticker"]), w["move"])
            w.update(p)
            if p["psych"] >= 65 and (w["move"] or 0) > 0.05:
                w["score"] = max(0, w["score"] - 10); w["reasons"].append("Rise isn't backed by the numbers (hype risk)")
            elif p["psych"] <= 35:
                w["score"] = min(100, w["score"] + 5); w["reasons"].append("The numbers back the move")
        ev["winners"].sort(key=lambda x: -x["score"])
        ev["loser_tickers"] = events.losers_for(ev, playbooks)
        print(f"    {ev['label']}: {len(ev['winners'])} winners ranked")

    print("4/6 Checking each dropped stock (news, financials, insiders, analysts, SEC)...")
    lib = Library()
    for d in drops:
        t = d["ticker"]
        news = details.news(t, cfg["lookback_days"])
        d["bucket"], d["keywords"] = classify.classify(news)
        d["headlines"] = [x["headline"] for x in news[:5]]
        d["_news"] = news
        d["insiders"] = details.insiders(t)
        d["rec_change"] = details.recommendations(t)
        d["metrics"] = details.metrics(t)
        d["red_flags"] = sec.filings(t)["red_flags"]
        d["event"] = next((ev["label"] for ev in live if t in ev["loser_tickers"]), None)
        d.update(score(d, lib, cfg))
        p = psych_score(d["metrics"], details.earnings_surprises(t), d["drop"],
                        extra_bad=["SEC red-flag filing"] if d["red_flags"] else ())
        d.update(p)
        if p["psych"] >= 65:
            d["score"] = min(100, d["score"] + 8); d["reasons"].append("Numbers still healthy: drop looks like psychology")
        elif p["psych"] <= 35:
            d["score"] = max(0, d["score"] - 8); d["reasons"].append("The numbers explain the drop")
        if d["event"]:
            d["reasons"].append(f"Part of a live event: {d['event']}")
    drops.sort(key=lambda x: -x["score"])

    print("5/6 Claude review of the top names (if ANTHROPIC_API_KEY is set)...")
    for d in drops[: cfg["claude_max_stocks"]]:
        c = claude.review(d, d["_news"], d, cfg)
        if c:
            d["claude"] = c
            d["score"] = max(0, min(100, d["score"] + c["adjust"]))
    drops.sort(key=lambda x: -x["score"])

    print("6/6 Paper portfolio + report...")
    paper = Paper(paper_path)
    added = paper.add(asof, [d for d in drops if d["score"] >= cfg["paper_buy_min_score"]], "rebound")
    for ev in live:
        added += paper.add(asof, [w for w in ev["winners"] if w["score"] >= cfg["paper_winner_min_score"]],
                           "event_winner")
    paper.mark(store, asof)
    paper.save()
    stats = {"all": paper.stats(), "rebound": paper.stats("rebound"), "event_winner": paper.stats("event_winner")}
    path = report.write(asof, live, drops, warnings, stats)
    print(f"    {len(live)} live events, {len(drops)} rebound candidates, {len(warnings)} early warnings, "
          f"{added} new paper picks")
    if not args.demo:
        notify.send(asof, live, drops, warnings, stats)
    print(f"Done -> {path}")


if __name__ == "__main__":
    main()
