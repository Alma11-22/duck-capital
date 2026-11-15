"""Read headlines: (1) what kind of bad news is this, (2) how negative is it."""
import re

# Bucket keywords. Order matters: first strong match wins ties.
BUCKETS = {
    "short_report": ["short seller", "short-seller", "short report", "hindenburg", "muddy waters",
                     "accounting", "restate", "auditor", "fraud", "sec investigation", "sec probe"],
    "bad_press": ["boycott", "backlash", "scandal", "lawsuit", "sued", "recall", "outbreak", "outage",
                  "probe", "investigation", "ceo resign", "ceo steps down", "ceo ousted", "viral",
                  "controversy", "allegation", "harassment", "shooting", "spy", "fined", "settlement"],
    "ai_fear": ["ai disruption", "disrupt", "chatgpt", "openai", "deepseek", "ai agent", "generative ai",
                "replaced by ai", "ai threat", "ai capex", "ai spending", "anthropic", "gemini"],
    "macro_policy": ["tariff", "trade war", "export control", "sanction", "fda", "regulator", "regulation",
                     "antitrust", "doj", "ftc", "medicare", "medicaid", "tax", "interest rate", "fed ",
                     "election", "policy", "ban"],
    "business_miss": ["guidance", "misses", "miss ", "cuts outlook", "lowers outlook", "sales decline",
                      "weak demand", "slowdown", "margin", "layoffs", "writedown", "impairment",
                      "downgrade", "competition", "loses share", "subscriber"],
}

NEGATIVE = {  # word -> weight
    "plunge": 2, "plunges": 2, "plummet": 2, "tumble": 2, "crash": 2, "sink": 1, "sinks": 1, "slide": 1,
    "slump": 1, "fall": 1, "falls": 1, "drop": 1, "drops": 1, "selloff": 1,
    "investigation": 3, "probe": 3, "subpoena": 3, "fraud": 3, "lawsuit": 2, "sued": 2, "class action": 1,
    "recall": 2, "boycott": 2, "backlash": 2, "scandal": 3, "breach": 2, "hack": 2, "outage": 2,
    "short seller": 3, "short-seller": 3, "short report": 3, "restate": 3, "auditor": 2,
    "resign": 2, "resigns": 2, "steps down": 2, "ousted": 2, "fired": 2, "departure": 1,
    "cuts guidance": 3, "cuts outlook": 3, "lowers guidance": 3, "lowers outlook": 3, "warns": 2,
    "misses": 2, "downgrade": 2, "downgraded": 2, "tariff": 1, "ban": 2, "delist": 3, "bankrupt": 3,
    "layoffs": 1, "writedown": 2, "impairment": 2, "halt": 2, "fda rejects": 3, "complete response letter": 3,
}
POSITIVE = ["beats", "raises guidance", "raises outlook", "record", "upgrade", "upgraded", "buyback",
            "approval", "approves", "wins contract", "partnership"]


def _text(items):
    return " ".join((n.get("headline", "") + " " + n.get("summary", "")).lower() for n in items)


def classify(news):
    """Return (bucket, matched_keywords). Defaults to business_miss."""
    text = _text(news)
    best, hits_best = "business_miss", []
    for bucket, words in BUCKETS.items():
        hits = [w for w in words if w in text]
        if len(hits) > len(hits_best):
            best, hits_best = bucket, hits
    return best, hits_best


def negativity(news):
    """Simple headline score: + for negative words, - for positive ones. Returns (score, top headlines)."""
    score, flagged = 0, []
    for n in news:
        h = (n.get("headline", "") + " " + n.get("summary", "")).lower()
        s = sum(w for k, w in NEGATIVE.items() if re.search(r"\b" + re.escape(k), h))
        s -= sum(1 for k in POSITIVE if k in h)
        if s > 0:
            flagged.append((s, n.get("headline", "")))
        score += max(s, 0)
    flagged.sort(reverse=True)
    return score, [h for _, h in flagged[:3]]
