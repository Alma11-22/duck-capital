"""Psychology vs. fundamentals: is the stock moving on the numbers, or on mood?

Reads the company's financials and compares them with how far the stock moved.
  Score 0-100.  High = the move is mostly PSYCHOLOGY (the numbers don't justify it).
                Low  = the move is mostly FUNDAMENTALS (the numbers back it up).

For a stock that DROPPED: healthy numbers + big drop  -> high score (overreaction).
For a stock that ROSE:    weak numbers + big jump     -> high score (hype).
"""


def _health(m, surprises):
    """How healthy the business looks right now: -5 (bad) .. +5 (good), with reasons."""
    pts, good, bad = 0, [], []
    g = m.get("revenue_growth")
    if g is not None:
        if g > 3:
            pts += 1; good.append(f"Revenue growing {g:.0f}% a year")
        elif g < -3:
            pts -= 1; bad.append(f"Revenue shrinking {g:.0f}% a year")
    e = m.get("eps_growth")
    if e is not None:
        if e > 3:
            pts += 1; good.append(f"Earnings growing {e:.0f}% a year")
        elif e < -10:
            pts -= 1; bad.append(f"Earnings down {e:.0f}% a year")
    mt, m5 = m.get("margin_ttm"), m.get("margin_5y")
    if mt is not None and m5 is not None:
        if mt >= m5 - 1:
            pts += 1; good.append(f"Profit margin holding ({mt:.0f}% vs {m5:.0f}% 5-yr avg)")
        elif mt < m5 - 4:
            pts -= 1; bad.append(f"Profit margin squeezed ({mt:.0f}% vs {m5:.0f}% 5-yr avg)")
    if surprises:
        beats = sum(1 for a, est in surprises if a >= est)
        if beats == len(surprises) and len(surprises) >= 2:
            pts += 1; good.append(f"Beat earnings estimates {beats} of last {len(surprises)} quarters")
        elif beats <= len(surprises) / 2:
            pts -= 1; bad.append(f"Missed earnings estimates {len(surprises) - beats} of last {len(surprises)} quarters")
    de = m.get("debt_to_equity")
    if de is not None:
        if de < 0.6:
            pts += 1; good.append("Low debt")
        elif de > 2:
            pts -= 1; bad.append("Heavy debt")
    return pts, good, bad


def psych_score(m, surprises, move, extra_bad=()):
    """move: the stock's % change (negative for a drop). Returns dict with score, label, reasons."""
    m = m or {}
    pts, good, bad = _health(m, surprises)
    bad = bad + list(extra_bad)
    pts -= len(extra_bad)
    size = min(abs(move) / 0.30, 1.0) if move is not None else 0.5  # how big the move is (0..1)
    # Stricter: one good number is not enough. Net health must be +2 or better before a drop
    # counts as psychology, and each point is worth less than before.
    eff = pts - 1 if pts > 0 else pts
    if move is not None and move < 0:   # a drop: healthy numbers => psychology
        s = 50 + eff * 6 * (0.5 + size)
    else:                               # a rise: weak numbers => hype (psychology)
        s = 50 - eff * 6 * (0.5 + size)
    s = max(0, min(100, round(s)))
    if s >= 68 and len(good) >= 3 and len(bad) <= 1:
        label = "Mostly psychology" if (move or 0) < 0 else "Mostly hype"
    elif s <= 35:
        label = "Mostly fundamentals"
    else:
        label = "Mixed"
        s = min(s, 67)
    data_points = sum(v is not None for v in (m.get("revenue_growth"), m.get("eps_growth"),
                                              m.get("margin_ttm"), m.get("debt_to_equity"))) + bool(surprises)
    if data_points < 2:
        label, s = "Not enough data", 50
    return {"psych": s, "psych_label": label, "numbers_good": good, "numbers_bad": bad}
