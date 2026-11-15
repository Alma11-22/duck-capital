"""Rebound AI - daily run.

    python run.py           # real data (needs MASSIVE_API_KEY and FINNHUB_API_KEY)
    python run.py --demo    # fake data, no keys needed

Both scanners run at the same time; results land in reports/latest.html.
"""
import argparse
import concurrent.futures as cf
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rebound import classify, claude, notify, report  # noqa: E402
from rebound.portfolio import Paper  # noqa: E402
from rebound.prices import PriceStore  # noqa: E402
from rebound.scanners import drop_scan, early_warning_scan  # noqa: E402
from rebound.score import Library, score  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="run on fake data")
    args = ap.parse_args()
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    cfg = yaml.safe_load(open("config.yaml"))

    if args.demo:
        from rebound.providers.mock import Mock
        prices = details = sec = Mock()
        db = "data/demo_prices.db"
        paper_path = "data/demo_paper_portfolio.csv"
        cfg["watchlist"] = ["CCC", "DDD"]
    else:
        from rebound.providers.finnhub import Finnhub
        from rebound.providers.massive import Massive
        from rebound.providers.sec import SEC
        prices, details, sec = Massive(), Finnhub(), SEC()
        db, paper_path = "data/prices.db", "data/paper_portfolio.csv"

    print("1/5 Updating prices for all US stocks...")
    store = PriceStore(db)
    n = store.update(prices, cfg["lookback_days"])
    window, asof = store.window(cfg["lookback_days"])
    print(f"    fetched {n} new day(s); {len(window)} tickers as of {asof}")
    if not window:
        sys.exit("No price data yet. Check MASSIVE_API_KEY, or run after midnight US Eastern.")

    print("2/5 Running both scanners at the same time...")
    with cf.ThreadPoolExecutor(max_workers=2) as pool:
        f_drop = pool.submit(drop_scan, window, details, cfg)
        f_warn = pool.submit(early_warning_scan, window, details, sec, cfg, classify.negativity)
        drops, warnings = f_drop.result(), f_warn.result()

    print("3/5 Checking each candidate (news, insiders, analysts, balance sheet, SEC)...")
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
        d.update(score(d, lib, cfg))
    drops.sort(key=lambda x: -x["score"])

    print("4/5 Claude review of the top names (if ANTHROPIC_API_KEY is set)...")
    for d in drops[: cfg["claude_max_stocks"]]:
        c = claude.review(d, d["_news"], d, cfg)
        if c:
            d["claude"] = c
            d["score"] = max(0, min(100, d["score"] + c["adjust"]))
    drops.sort(key=lambda x: -x["score"])

    print("5/5 Paper portfolio + report...")
    paper = Paper(paper_path)
    added = paper.add(asof, [d for d in drops if d["score"] >= cfg["paper_buy_min_score"]])
    paper.mark(store, asof)
    paper.save()
    path = report.write(asof, drops, warnings, paper.stats())
    print(f"    {len(drops)} rebound candidates, {len(warnings)} early warnings, {added} new paper picks")
    if not args.demo:
        notify.send(asof, drops, warnings, paper.stats())
    print(f"Done -> {path}")


if __name__ == "__main__":
    main()
