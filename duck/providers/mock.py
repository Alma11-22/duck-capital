"""Fake data so the whole pipeline runs without any API keys (demo/testing).
The demo market is in the middle of a tariff shock."""
import datetime as dt
import random

TICKERS = {
    # ticker: (name, industry, mcap $M, pattern)
    "AAA": ("Acme Analytics", "Software", 45000, "ai_drop"),
    "BBB": ("Bolt Beverages", "Beverages", 12000, "scandal_drop"),
    "AAPL": ("Apple", "Technology", 3000000, "tariff_drop"),
    "NKE": ("Nike", "Apparel", 90000, "tariff_drop"),
    "DDD": ("Delta Devices", "Technology", 8000, "early_warning"),
    "EEE": ("Echo Energy", "Energy", 25000, "flat"),
    "FFF": ("Forge Foods", "Food", 6000, "miss_drop"),
    "GGG": ("Gamma Gene", "Biotech", 1500, "miss_drop"),  # too small, filtered out
    "NUE": ("Nucor", "Steel", 35000, "win_up"),
    "STLD": ("Steel Dynamics", "Steel", 20000, "win_late"),
    "TJX": ("TJX Companies", "Retail", 130000, "flat"),
    "WMT": ("Walmart", "Retail", 700000, "win_up"),
    "ROST": ("Ross Stores", "Retail", 45000, "win_up"),
}
MOVE = {"ai_drop": -0.28, "scandal_drop": -0.18, "tariff_drop": -0.16, "miss_drop": -0.35,
        "early_warning": -0.03, "flat": 0.0, "win_up": 0.07, "win_late": 0.40}

NEWS = {
    "ai_drop": ["New AI agents threaten seat-based software, analysts warn",
                "Acme shares slide as investors fear AI disruption"],
    "scandal_drop": ["Bolt Beverages faces boycott after viral ad backlash",
                     "Celebrity calls for boycott of Bolt drinks"],
    "tariff_drop": ["Shares sink on new tariff announcement",
                    "Tariffs weigh on outlook despite strong demand"],
    "early_warning": ["Delta Devices CFO resigns unexpectedly",
                      "SEC opens investigation into Delta Devices accounting",
                      "Short seller publishes report on Delta Devices"],
    "miss_drop": ["Forge Foods cuts full-year guidance, sales decline",
                  "Forge Foods misses estimates as volumes fall"],
    "flat": ["Company announces dividend"],
    "win_up": ["Domestic producers seen as tariff winners"],
    "win_late": ["Steel stocks soar on tariff protection"],
}
MARKET_NEWS = [
    "White House announces sweeping tariffs on imports; China vows retaliatory duties",
    "Markets tumble as trade war fears grow",
    "Retailers warn tariffs will raise prices; import duties hit apparel makers",
    "Steelmakers rally as tariffs shield domestic producers",
    "Analysts: trade war could last months as talks stall",
]


class Mock:
    def __init__(self, seed=7):
        self.rng = random.Random(seed)
        self.today = dt.date.today()

    def daily_bars(self, date):
        d = dt.date.fromisoformat(date)
        if d.weekday() >= 5:
            return {}
        age = (self.today - d).days
        out = {}
        for t, (_, _, _, pat) in TICKERS.items():
            frac = max(0.0, min(1.0, (20 - age) / 15))  # the move happens over the last ~2 weeks
            c = 100.0 * (1 + MOVE[pat] * frac) * (1 + self.rng.uniform(-0.005, 0.005))
            out[t] = {"close": round(c, 2), "high": round(c * 1.01, 2), "volume": 2_000_000}
        out["PENNY"] = {"close": 1.2, "high": 1.3, "volume": 10_000}
        return out

    def profile(self, t):
        n, ind, cap, _ = TICKERS.get(t, (t, "", 0, "flat"))
        return {"name": n, "industry": ind, "market_cap_musd": cap}

    def news(self, t, days=3):
        pat = TICKERS.get(t, ("", "", 0, "flat"))[3]
        return [{"headline": h, "summary": "", "source": "MockWire", "url": "",
                 "date": self.today.isoformat()} for h in NEWS[pat]]

    def market_news(self, days=2):
        return [{"headline": h, "summary": "", "source": "MockWire", "url": ""} for h in MARKET_NEWS]

    def metrics(self, t):
        return {"debt_to_equity": self.rng.choice([0.2, 0.6, 1.8]), "current_ratio": 1.4,
                "pe": 18, "revenue_growth": self.rng.choice([-2, 8]), "high_52w": 110,
                "eps_growth": {"AAPL": 9, "AAA": 12, "FFF": -25, "STLD": -5}.get(t, 4),
                "margin_ttm": {"FFF": 3}.get(t, 15), "margin_5y": 14, "roe": 20}

    def earnings_surprises(self, t):
        if t in ("FFF", "STLD"):
            return [(0.8, 1.0), (0.9, 1.0)]
        return [(1.1, 1.0), (1.05, 1.0), (0.98, 1.0)]

    def recommendations(self, t):
        return self.rng.choice([-3, 0, 2])

    def insiders(self, t, days=90):
        return {"AAA": 50000, "BBB": 0, "AAPL": 12000, "FFF": -80000}.get(t, 0)

    def filings(self, t, days=30):
        if t == "DDD":
            return {"red_flags": [f"{self.today}: Executive / director departure (8-K 5.02)"], "form4_count": 6}
        return {"red_flags": [], "form4_count": 1}
