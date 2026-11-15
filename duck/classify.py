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
    "macro_policy": ["tariff", "trade war", "export control", "export ban", "sanction", "fda reject",
                     "fda approval", "complete response letter", "antitrust", "doj sues", "ftc sues",
                     "medicare", "medicaid", "drug pricing", "rate hike", "rate cut", "federal reserve",
                     "treasury yields", "bond yields", "executive order", "government shutdown"],
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
    """Return (bucket, matched_keywords).

    A bucket needs 2+ distinct keyword hits to win; ties go to business_miss
    (the most conservative bucket). Otherwise defaults to business_miss.
    """
    text = _text(news)
    scored = []
    for bucket, words in BUCKETS.items():
        hits = [w for w in words if re.search(r"\b" + re.escape(w.strip()), text)]
        scored.append((len(hits), bucket == "business_miss", bucket, hits))
    scored.sort(reverse=True)
    n, _, bucket, hits = scored[0]
    if n < 2 and bucket != "business_miss":
        return "business_miss", hits
    return bucket, hits


GENERIC = {"bank", "first", "american", "general", "united", "international", "national", "global",
           "new", "the", "royal", "energy", "capital", "financial", "southern", "western", "eastern"}
SOURCE_VERBS = (r"analyst|strategist|economist|research|securities|says|said|warn|see|expect|cut|slash|"
                r"raise|lift|trim|downgrade|upgrade|initiate|reiterate|predict|forecast|note|top pick|price target")


def _names(ticker, name):
    n = re.sub(SUFFIX, "", (name or "").lower()).replace(",", " ")
    n = re.sub(r"\s+", " ", n).strip()
    out = [ticker.lower()]
    if n:
        out.append(n)
        w = n.split()[0]
        if len(w) >= 4 and w not in GENERIC:
            out.append(w)
    alias = {"BAC": "bofa", "GS": "goldman", "MS": "morgan stanley", "JPM": "jpmorgan", "C": "citi",
             "WFC": "wells fargo", "GOOGL": "google", "GOOG": "google", "META": "facebook"}.get(ticker)
    if alias:
        out.append(alias)
    return sorted(set(out), key=len, reverse=True)


def about(news, ticker, name):
    """Keep only headlines actually ABOUT this company, not ones where it is just the source
    (e.g. 'Bank of America analysts cut Nike' is not news about Bank of America)."""
    alt = "|".join(re.escape(x) for x in _names(ticker, name))
    hit = re.compile(r"\b(" + alt + r")\b", re.I)
    src = re.compile(r"\b(" + alt + r")('s)?\s+(global\s+)?(" + SOURCE_VERBS + r")|"
                     r"\b(according to|by|from|at|says|said|warns)\s+(" + alt + r")\b|"
                     r",\s*(" + alt + r")\s+(" + SOURCE_VERBS + r")", re.I)
    out = []
    for n in news:
        h = n.get("headline", "")
        if not hit.search(h):
            continue
        if src.search(h) and len(hit.findall(h)) == 1:
            continue  # company only appears as the source of the story
        out.append(n)
    return out


SUFFIX = r"\b(inc|incorporated|corp|corporation|co|company|plc|ltd|limited|holdings?|group|n\.?v|s\.?a|ag|se|class [a-c]|the)\b\.?"


def negativity(news):
    """Simple headline score: + for negative words, - for positive ones. Returns (score, top headlines).
    Each headline counts at most 4, so a flood of stories can't run the score up on its own."""
    score, flagged = 0, []
    for n in news:
        h = (n.get("headline", "") + " " + n.get("summary", "")).lower()
        s = sum(w for k, w in NEGATIVE.items() if re.search(r"\b" + re.escape(k), h))
        s -= sum(1 for k in POSITIVE if k in h)
        if s > 0:
            flagged.append((s, n.get("headline", "")))
        score += min(max(s, 0), 4)
    flagged.sort(reverse=True)
    return score, [h for _, h in flagged[:3]]


SERIOUS = ["investigation", "probe", "subpoena", "fraud", "lawsuit", "sued", "class action", "recall",
           "cuts guidance", "lowers guidance", "cuts outlook", "lowers outlook", "slashes forecast", "warns",
           "resigns", "steps down", "ousted", "fired", "short seller", "short-seller", "short report",
           "restate", "auditor", "delist", "bankrupt", "chapter 11", "fda rejects", "complete response letter",
           "breach", "hack", "outage", "boycott", "backlash", "scandal", "halt", "default", "going concern"]


GOOD = ["beat", "beats", "raise", "raises", "raised", "upgrade", "upgraded", "record", "soar", "soars", "surge",
        "surges", "jump", "jumps", "rally", "rallies", "crushed", "crushes", "wins", "approval", "approved",
        "demonstrated", "positive", "outperform"]


def serious(news, ticker=None, name=None):
    """Headlines with company-level news that tends to move a stock.
    Whole words only; skips good-news headlines; if ticker/name given, the bad word must sit in the
    same part of the headline as the company (so 'X resigns from Nvidia, Microsoft faces...' isn't Microsoft's)."""
    word = lambda k: re.compile(r"\b" + re.escape(k) + r"(s|es|ed|ing)?\b", re.I)
    bad_res = [word(k) for k in SERIOUS]
    good_re = re.compile(r"\b(" + "|".join(map(re.escape, GOOD)) + r")\b", re.I)
    who = None
    if ticker:
        who = re.compile(r"\b(" + "|".join(re.escape(x) for x in _names(ticker, name)) + r")\b", re.I)
    out = []
    for n in news:
        h = n.get("headline", "")
        if good_re.search(h):
            continue
        parts = re.split(r"[,;:|]| - | – | — ", h) if who else [h]
        for part in parts:
            if any(r.search(part) for r in bad_res) and (who is None or who.search(part)):
                out.append(h)
                break
    return out
