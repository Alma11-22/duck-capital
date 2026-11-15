"""Massive (formerly Polygon.io) - free 'Stocks Basic' plan.

One 'grouped daily' call returns the end-of-day bar for every US stock.
Free plan: 5 calls/minute, end-of-day only (yesterday's data is available
after midnight US Eastern time).
"""
import os

from ..http import get_json

BASE = "https://api.polygon.io/v2/aggs/grouped/locale/us/market/stocks/{date}"


class Massive:
    def __init__(self, api_key=None):
        self.key = api_key or os.environ.get("MASSIVE_API_KEY") or os.environ.get("POLYGON_API_KEY")
        if not self.key:
            raise RuntimeError("Set MASSIVE_API_KEY (free key at massive.com)")

    def daily_bars(self, date):
        """All US stocks for one trading day. Returns {} on holidays/weekends."""
        data = get_json(BASE.format(date=date), {"adjusted": "true", "apiKey": self.key},
                        min_interval=12.5)  # stay under 5 calls/minute
        if not data or not data.get("results"):
            return {}
        out = {}
        for r in data["results"]:
            t = r.get("T")
            if t and r.get("c"):
                out[t] = {"close": r["c"], "high": r.get("h", r["c"]), "volume": r.get("v", 0)}
        return out
