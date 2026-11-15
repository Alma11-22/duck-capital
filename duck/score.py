"""Recovery score (0-100) and buy plan, based on our case library plus hard checks.

Starts from how often that kind of selloff recovered in the library, then
adjusts for evidence that the business itself is (or isn't) hurt.
"""
import csv

BUCKET_LABEL = {
    "bad_press": "Bad press / scandal",
    "short_report": "Short report / accounting",
    "ai_fear": "AI disruption fear",
    "macro_policy": "Macro / policy",
    "business_miss": "Business miss",
}

EXIT_TRIGGERS = {
    "bad_press": "Customers actually leave: sales/traffic data falls for 2 straight quarters, or the scandal widens.",
    "short_report": "Auditor resigns, results restated, or regulator charges filed.",
    "ai_fear": "Revenue growth slows or customers shrink seats/contracts in the next 2 reports.",
    "macro_policy": "The policy becomes permanent AND guidance is cut because of it.",
    "business_miss": "A second guidance cut, or market share keeps falling to a named competitor.",
}


class Library:
    def __init__(self, path="data/library.csv"):
        self.cases = list(csv.DictReader(open(path)))
        for c in self.cases:
            c["drop"] = float(c["drop"])
            c["vs_before"] = float(c["vs_before"])
            c["recovered"] = int(c["recovered"])

    def base_rate(self, bucket):
        cs = [c for c in self.cases if c["bucket"] == bucket]
        if not cs:
            return 0.4, 0
        return sum(c["recovered"] for c in cs) / len(cs), len(cs)

    def analogs(self, bucket, drop, n=3):
        """Closest past cases: same kind of news, most similar drop size."""
        cs = [c for c in self.cases if c["bucket"] == bucket] or self.cases
        cs = sorted(cs, key=lambda c: abs(c["drop"] - drop))[:n]
        return [f'{c["ticker"]} ({c["drop"]:.0%} drop → {c["vs_before"]:+.0%} vs. before)' for c in cs]


def score(stock, lib, cfg):
    """stock: dict with drop, bucket, insiders, rec_change, metrics, red_flags, neg_score."""
    reasons = []
    rate, n = lib.base_rate(stock["bucket"])
    s = 20 + rate * 60  # 20..80 from the base rate
    reasons.append(f"{BUCKET_LABEL[stock['bucket']]} selloffs recovered {rate:.0%} of the time ({n} past cases)")

    drop = -stock["drop"]
    if drop >= 0.30:
        s += 6; reasons.append("Deep drop (30%+): more room to recover")
    elif drop < 0.15:
        s -= 4; reasons.append("Shallow drop: less upside")

    ins = stock.get("insiders")
    if ins is not None:
        if ins > 0:
            s += 10; reasons.append("Insiders are buying")
        elif ins < 0:
            s -= 4; reasons.append("Insiders are selling")

    rc = stock.get("rec_change")
    if rc is not None:
        if rc > 0:
            s += 5; reasons.append("Analysts upgrading")
        elif rc < -2:
            s -= 8; reasons.append("Analysts downgrading")

    m = stock.get("metrics") or {}
    de, cr = m.get("debt_to_equity"), m.get("current_ratio")
    if de is not None and de > 1.5:
        s -= 8; reasons.append("High debt: less able to ride it out")
    elif de is not None and de < 0.5:
        s += 4; reasons.append("Low debt")
    if cr is not None and cr < 1.0:
        s -= 4; reasons.append("Tight short-term cash (current ratio < 1)")
    g = m.get("revenue_growth")
    if g is not None and g < 0:
        s -= 6; reasons.append("Revenue shrinking")

    if stock.get("red_flags"):
        s -= 10; reasons.append("SEC red-flag filing: " + stock["red_flags"][0])

    s = max(0, min(100, round(s)))
    price = stock["close"]
    plan = [round(price * (1 + t), 2) for t in cfg["tranches"]]
    return {
        "score": s,
        "reasons": reasons,
        "analogs": lib.analogs(stock["bucket"], stock["drop"]),
        "buy_plan": plan,
        "exit_trigger": EXIT_TRIGGERS[stock["bucket"]],
    }
