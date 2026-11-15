"""The two scanners. They run at the same time (see run.py).

1. Drop scanner:  stocks already down >= threshold from their recent high.
2. Early warning: stocks with bad news that have NOT dropped much yet.
"""


def drop_scan(window, details, cfg, log=print):
    """window: {ticker: {close, high, dollar_volume}} from PriceStore."""
    cands = []
    for t, w in window.items():
        if not t.isalpha() or len(t) > 5:  # skip warrants, units, preferreds
            continue
        if w["close"] < cfg["min_price"] or w["dollar_volume"] < cfg["min_dollar_volume"]:
            continue
        drop = w["close"] / w["high"] - 1 if w["high"] else 0
        if drop <= -cfg["drop_threshold"]:
            cands.append((t, drop, w))
    # Biggest, most-traded names first so the API budget goes to what matters
    cands.sort(key=lambda x: -x[2]["dollar_volume"])
    log(f"  drop scan: {len(cands)} stocks down {cfg['drop_threshold']:.0%}+; checking top {cfg['max_candidates']}")
    out = []
    for t, drop, w in cands[: cfg["max_candidates"]]:
        p = details.profile(t)
        if p["market_cap_musd"] < cfg["min_market_cap_musd"]:
            continue
        out.append({"ticker": t, "name": p["name"], "industry": p["industry"],
                    "market_cap_musd": p["market_cap_musd"], "close": w["close"],
                    "high": w["high"], "drop": drop})
    log(f"  drop scan: {len(out)} pass the ${cfg['min_market_cap_musd']/1000:.0f}B+ size filter")
    return out


def early_warning_scan(window, details, sec, cfg, negativity, about=None, log=print):
    """Watchlist + most-traded names: alert on bad news before a big drop."""
    liquid = sorted((t for t in window if t.isalpha()), key=lambda t: -window[t]["dollar_volume"])
    universe = list(dict.fromkeys(cfg["watchlist"] + liquid[: cfg["early_warning_top_n"]]))
    log(f"  early warning: reading news for {len(universe)} stocks")
    out = []
    for t in universe:
        w = window.get(t)
        if not w:
            continue
        drop = w["close"] / w["high"] - 1 if w["high"] else 0
        if drop <= -cfg["early_warning_max_drop"]:
            continue  # already dropped: the drop scanner covers it
        news = details.news(t, cfg["news_days"])
        if about:
            news = about(news, t, details.profile(t)["name"])
        neg, top = negativity(news)
        filings = sec.filings(t, days=cfg["news_days"] + 4)
        neg += 3 * len(filings["red_flags"])
        if neg >= cfg["early_warning_min_score"]:
            out.append({"ticker": t, "close": w["close"], "drop": drop, "neg_score": neg,
                        "headlines": top, "red_flags": filings["red_flags"],
                        "on_watchlist": t in cfg["watchlist"]})
    out.sort(key=lambda x: -x["neg_score"])
    log(f"  early warning: {len(out)} alerts")
    return out
