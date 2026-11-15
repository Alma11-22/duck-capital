"""Event radar + event winners.

1. Read the day's market-wide headlines and score them against each playbook.
2. Check the market agrees: the playbook's losers fell and its winners held up.
3. For each live event, rank the winners (direct and second-order) and tag the losers.
"""
import re

import yaml


def load_playbooks(path="data/event_playbooks.yaml"):
    return yaml.safe_load(open(path))


def _hits(text, keywords):
    return [k for k in keywords if re.search(r"\b" + re.escape(k.lower()), text)]


def _basket_move(store, tickers, days):
    moves = [m for m in (store.change(t, days) for t in tickers) if m is not None]
    return (sum(moves) / len(moves), len(moves)) if moves else (None, 0)


def detect(news, playbooks, store, cfg, log=print):
    """Return live events, strongest first."""
    events = []
    for key, pb in playbooks.items():
        score, quotes = 0, []
        for n in news:
            h = (n.get("headline", "") + " " + n.get("summary", "")).lower()
            hits = _hits(h, pb["keywords"])
            if hits:
                score += len(hits)
                quotes.append(n.get("headline", ""))
        if score < cfg["event_min_score"]:
            continue
        d = cfg["event_confirm_days"]
        lose_mv, _ = _basket_move(store, pb.get("losers", []), d)
        win_mv, _ = _basket_move(store, pb["winners"]["direct"] + pb["winners"]["second_order"], d)
        confirmed = (lose_mv is not None and win_mv is not None and win_mv - lose_mv > 0.03)
        events.append({"key": key, "label": pb["label"], "score": score, "headlines": quotes[:4],
                       "losers_move": lose_mv, "winners_move": win_mv, "confirmed": confirmed,
                       "past": pb.get("past", ""), "sell_when": pb["sell_when"]})
    events.sort(key=lambda e: (-int(e["confirmed"]), -e["score"]))
    log(f"  event radar: {len(events)} live event(s)" +
        (": " + ", ".join(e["label"] for e in events) if events else ""))
    return events


def rank_winners(event, playbooks, store, details, cfg, extra=None):
    """Score each candidate winner for one event. extra: [(ticker, reason)] from Claude."""
    pb = playbooks[event["key"]]
    cands = [(t, "direct", "") for t in pb["winners"]["direct"]] + \
            [(t, "second_order", "") for t in pb["winners"]["second_order"]] + \
            [(t, "claude", why) for t, why in (extra or [])]
    seen, out = set(), []
    d = cfg["event_confirm_days"]
    for t, kind, why in cands:
        if t in seen:
            continue
        seen.add(t)
        px = store.latest(t)
        if px is None:
            continue
        mv = store.change(t, d)
        mv_month = store.change(t, 21)
        s = {"direct": 60, "second_order": 55, "claude": 50}[kind]
        reasons = [{"direct": "Benefits directly from this kind of event",
                    "second_order": "Second-order beneficiary (less obvious, often less crowded)",
                    "claude": f"Claude idea: {why}"}[kind]]
        if mv_month is not None and mv_month > cfg["winner_chase_limit"]:
            s -= 15; reasons.append(f"Already up {mv_month:.0%} this month: late, likely priced in")
        elif mv is not None:
            if mv > cfg["winner_chase_limit"]:
                s -= 15; reasons.append(f"Already up {mv:.0%}: late, likely priced in")
            elif mv > 0.03:
                s += 10; reasons.append(f"Up {mv:.0%}: market starting to agree")
            elif mv < -0.03:
                s -= 5; reasons.append(f"Down {mv:.0%}: market not buying it yet")
            else:
                s += 5; reasons.append("Hasn't moved yet: early")
        if event["confirmed"]:
            s += 10; reasons.append("Market confirms the event (losers down, winners up)")
        m = details.metrics(t) or {}
        g = m.get("revenue_growth")
        if g is not None and g > 0:
            s += 5; reasons.append("Revenue growing")
        de = m.get("debt_to_equity")
        if de is not None and de > 2:
            s -= 5; reasons.append("High debt")
        out.append({"ticker": t, "kind": kind, "close": px, "move": mv, "score": max(0, min(100, s)),
                    "reasons": reasons, "event": event["label"], "sell_when": event["sell_when"]})
    out.sort(key=lambda x: -x["score"])
    return out


def losers_for(event, playbooks):
    return set(playbooks[event["key"]].get("losers", []))
