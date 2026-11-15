"""Fake data so the whole pipeline can run without any API keys (demo/testing)."""
import datetime as dt
import random

TICKERS = {
    # ticker: (name, industry, mcap $M, pattern)
    "AAA": ("Acme Analytics", "Software", 45000, "ai_drop"),
    "BBB": ("Bolt Beverages", "Beverages", 12000, "scandal_drop"),
    "CCC": ("Crest Chips", "Semiconductors", 300000, "tariff_drop"),
    "DDD": ("Delta Devices", "Technology", 8000, "early_warning"),
    "EEE": ("Echo Energy", "Energy", 25000, "flat"),
    "FFF": ("Forge Foods", "Food", 6000, "miss_drop"),
    "GGG": ("Gamma Gene", "Biotech", 1500, "miss_drop"),  # too small, filtered out
}

NEWS = {
    "ai_drop": ["New AI agents threaten seat-based software, analysts warn",
                "Acme shares slide as investors fear AI disruption"],
    "scandal_drop": ["Bolt Beverages faces boycott after viral ad backlash",
                     "Celebrity calls for boycott of Bolt drinks"],
    "tariff_drop": ["Chip stocks sink on new tariff announcement",
                    "Crest Chips beats estimates; tariffs weigh on outlook"],
    "early_warning": ["Delta Devices CFO resigns unexpectedly",
                      "SEC opens investigation into Delta Devices accounting",
                      "Short seller publishes report on Delta Devices"],
    "miss_drop": ["Forge Foods cuts full-year guidance, sales decline",
                  "Forge Foods misses estimates as volumes fall"],
    "flat": ["Echo Energy announces dividend"],
}


class Mock:
    def __init__(self, seed=7):
        self.rng = random.Random(seed)
        self.today = dt.date.today()

    def daily_bars(self, date):
        d = dt.date.fromisoformat(date)
        if d.weekday() >= 5:
            return {}
        age = (self.today - d).days  # days before today
        out = {}
        for t, (_, _, _, pat) in TICKERS.items():
            base = 100.0
            drop = {"ai_drop": 0.28, "scandal_drop": 0.18, "tariff_drop": 0.15,
                    "miss_drop": 0.35, "early_warning": 0.03, "flat": 0.0}[pat]
            frac = max(0.0, min(1.0, (20 - age) / 15))  # drop happens over the last ~2 weeks
            c = base * (1 - drop * frac) * (1 + self.rng.uniform(-0.01, 0.01))
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

    def metrics(self, t):
        return {"debt_to_equity": self.rng.choice([0.2, 0.6, 1.8]), "current_ratio": 1.4,
                "pe": 18, "revenue_growth": 8, "high_52w": 110}

    def recommendations(self, t):
        return self.rng.choice([-3, 0, 2])

    def insiders(self, t, days=90):
        return {"AAA": 50000, "BBB": 0, "CCC": 12000, "FFF": -80000}.get(t, 0)

    def filings(self, t, days=30):
        if t == "DDD":
            return {"red_flags": [f"{self.today}: Executive / director departure (8-K 5.02)"], "form4_count": 6}
        return {"red_flags": [], "form4_count": 1}
