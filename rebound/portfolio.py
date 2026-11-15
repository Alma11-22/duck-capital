"""Paper portfolio: every high-score call is logged and tracked, so the hit rate is measured."""
import csv
import os

FIELDS = ["date", "ticker", "bucket", "score", "entry", "drop_at_entry", "last_price", "last_date", "return"]


class Paper:
    def __init__(self, path="data/paper_portfolio.csv"):
        self.path = path
        self.rows = list(csv.DictReader(open(path))) if os.path.exists(path) else []

    def add(self, date, picks):
        held = {r["ticker"] for r in self.rows}
        added = 0
        for p in picks:
            if p["ticker"] in held:
                continue
            self.rows.append({"date": date, "ticker": p["ticker"], "bucket": p["bucket"],
                              "score": p["score"], "entry": p["close"], "drop_at_entry": round(p["drop"], 3),
                              "last_price": p["close"], "last_date": date, "return": 0.0})
            added += 1
        return added

    def mark(self, store, date):
        for r in self.rows:
            px = store.close_on_or_before(r["ticker"], date)
            if px:
                r["last_price"], r["last_date"] = px, date
                r["return"] = round(px / float(r["entry"]) - 1, 4)

    def stats(self):
        if not self.rows:
            return {"n": 0, "hit_rate": None, "avg_return": None}
        rets = [float(r["return"]) for r in self.rows]
        return {"n": len(rets), "hit_rate": sum(x > 0 for x in rets) / len(rets),
                "avg_return": sum(rets) / len(rets)}

    def save(self):
        with open(self.path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(self.rows)
