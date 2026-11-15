"""Finnhub - free plan (60 calls/minute).

Used per company: profile (market cap, industry), news, basic financials,
analyst recommendation trends, and insider transactions (falls back to SEC
if the free plan refuses it).
"""
import datetime as dt
import os

from ..http import get_json

BASE = "https://finnhub.io/api/v1"


class Finnhub:
    def __init__(self, api_key=None):
        self.key = api_key or os.environ.get("FINNHUB_API_KEY")
        if not self.key:
            raise RuntimeError("Set FINNHUB_API_KEY (free key at finnhub.io)")

    def _get(self, path, **params):
        params["token"] = self.key
        return get_json(f"{BASE}/{path}", params, min_interval=1.1)

    def profile(self, ticker):
        p = self._get("stock/profile2", symbol=ticker) or {}
        return {"name": p.get("name", ticker), "industry": p.get("finnhubIndustry", ""),
                "market_cap_musd": p.get("marketCapitalization") or 0}

    def news(self, ticker, days=3):
        to = dt.date.today()
        frm = to - dt.timedelta(days=days)
        items = self._get("company-news", symbol=ticker, **{"from": frm.isoformat(), "to": to.isoformat()}) or []
        return [{"headline": n.get("headline", ""), "summary": n.get("summary", ""),
                 "source": n.get("source", ""), "url": n.get("url", ""),
                 "date": dt.datetime.fromtimestamp(n.get("datetime", 0)).date().isoformat()}
                for n in items[:40]]

    def metrics(self, ticker):
        m = (self._get("stock/metric", symbol=ticker, metric="all") or {}).get("metric", {})
        return {"debt_to_equity": m.get("totalDebt/totalEquityQuarterly"),
                "current_ratio": m.get("currentRatioQuarterly"),
                "pe": m.get("peTTM"),
                "revenue_growth": m.get("revenueGrowthTTMYoy"),
                "high_52w": m.get("52WeekHigh")}

    def recommendations(self, ticker):
        """Change in analyst buy ratings vs ~3 months ago (positive = upgrades)."""
        r = self._get("stock/recommendation", symbol=ticker) or []
        if len(r) < 2:
            return None
        buys = lambda x: x.get("strongBuy", 0) + x.get("buy", 0)
        sells = lambda x: x.get("strongSell", 0) + x.get("sell", 0)
        now, then = r[0], r[min(3, len(r) - 1)]
        return (buys(now) - sells(now)) - (buys(then) - sells(then))

    def insiders(self, ticker, days=90):
        """Net insider shares bought (+) or sold (-) on the open market. None if unavailable."""
        frm = (dt.date.today() - dt.timedelta(days=days)).isoformat()
        d = self._get("stock/insider-transactions", symbol=ticker, **{"from": frm})
        if not d or "data" not in d:
            return None
        net = 0
        for t in d["data"]:
            code = t.get("transactionCode")
            if code == "P":
                net += abs(t.get("change", 0))
            elif code == "S":
                net -= abs(t.get("change", 0))
        return net
