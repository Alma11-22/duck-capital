"""The Duck Capital desk: several Claude agents, each with one job, look at the same evidence.

Agents (each returns a stance, a small score nudge, a one-line headline and reasons):
  news         - what actually happened; company, sector or noise; one-off or lasting
  fundamentals - is the business itself hurt?
  bear         - the strongest case the stock keeps falling (stops cheerleading)
  historian    - closest past cases and what happened next
  event        - which live event it's tied to and what that means
  risk         - position size, concentration, and when the thesis breaks
Then the chair (portfolio manager) reads all six and makes the call: Buy / Watch / Pass,
moves the rules score by at most +/-15, and writes a short memo incl. disagreements.

The exit monitor checks every open paper pick each day: hold, trim or sell.
Only runs when ANTHROPIC_API_KEY is set. You still make every decision.
"""
import concurrent.futures as cf
import json

from . import claude

ROLES = {
    "news": ("News analyst",
             "Explain what actually happened to this stock. Is the news about the company itself, its whole "
             "sector, or just noise? Is it a one-off or likely to last? Ignore headlines that only mention "
             "the company in passing."),
    "fundamentals": ("Fundamentals analyst",
                     "Judge from the financial numbers only whether the business's earning power is actually "
                     "hurt, or whether the numbers still look healthy."),
    "bear": ("Bear",
             "Your job is to argue the strongest honest case that this stock keeps falling or is a value "
             "trap. Be specific. If you genuinely can't find a strong bear case, say so."),
    "historian": ("Historian",
                  "Compare this situation with the past cases given and with similar episodes you know of. "
                  "What usually happened next, and how long did it take?"),
    "event": ("Event strategist",
              "Relate this stock to the live market events given (or the lack of any). Does the event help "
              "or hurt it, and is that already priced in?"),
    "risk": ("Risk manager",
             "Recommend a position size as % of a portfolio (0-5%), note concentration with other picks in "
             "the same sector or event, and state the one concrete thing that would break the thesis."),
}

AGENT_PROMPT = """You are the {title} on a small event-driven stock desk. {job}
Use only the evidence below plus well-established general knowledge. Do not invent facts or numbers.

EVIDENCE
{evidence}

Reply with JSON only:
{{"stance": "bullish" | "neutral" | "bearish",
  "adjust": <integer -5..5, your nudge to the rules score>,
  "headline": "<one short line, max 15 words>",
  "reasons": ["<short reason citing the evidence>", "..."]{extra}}}"""

CHAIR_PROMPT = """You are the portfolio manager chairing an event-driven stock desk. Your analysts each
looked at the same stock. Weigh them (the bear's case deserves real weight), then make the call.

EVIDENCE
{evidence}

ANALYSTS
{views}

Rules score (from our tested rules): {score}/100. You may move it by at most 15 points either way,
and only for reasons the analysts cited.

Reply with JSON only:
{{"call": "Buy" | "Watch" | "Pass",
  "adjust": <integer -15..15>,
  "memo": "<max 3 sentences: the call and why>",
  "disagreement": "<one line on where the analysts disagreed, or empty>"}}"""

EXIT_PROMPT = """You are the exit monitor on a stock desk. We hold this paper position.
Ticker: {ticker} ({kind}). Bought {date} at ${entry:.2f}; now ${price:.2f} ({ret:+.1%}).
Why we bought: {reason}
Thesis breaks if: {trigger}
Live events now: {events}
Latest headlines:
{headlines}

Decide: hold, trim (take some profit / reduce risk) or sell (thesis broken or target reached).
Reply with JSON only: {{"action": "hold" | "trim" | "sell", "why": "<one short line>"}}"""


def evidence(d, live):
    """Plain-text evidence pack for one stock (rebound candidate or event winner)."""
    sc = d.get("sector_info") or {}
    m = d.get("metrics") or {}
    lines = [f"Stock: {d.get('name', d['ticker'])} ({d['ticker']}) {d.get('industry', '')}",
             f"Price ${d['close']:,.2f}"]
    if d.get("drop") is not None:
        lines.append(f"Down {d['drop']:.0%} from its 1-month high. Kind of drop: {d.get('bucket', '?')}.")
    if d.get("move") is not None:
        lines.append(f"5-day move {d['move']:+.0%}.")
    if sc:
        lines.append(f"Closest sector: {sc['sector']} ({sc['sector_drop']:+.0%} from its 1-month high).")
    if m:
        keep = {k: m.get(k) for k in ("revenue_growth", "eps_growth", "margin_ttm", "margin_5y",
                                      "debt_to_equity", "current_ratio", "pe", "roe") if m.get(k) is not None}
        lines.append("Financials (TTM %, ratios): " + json.dumps(keep))
    if d.get("numbers_good") or d.get("numbers_bad"):
        lines.append("Numbers read: " + "; ".join(d.get("numbers_good", []) + d.get("numbers_bad", [])))
    if d.get("insiders") is not None:
        lines.append(f"Insider net activity: {d['insiders']:+}")
    if d.get("red_flags"):
        lines.append("SEC red flags: " + "; ".join(d["red_flags"]))
    if d.get("analogs"):
        lines.append("Most similar past cases: " + ", ".join(d["analogs"]))
    lines.append("Rules-score reasons: " + "; ".join(d.get("reasons", [])))
    heads = d.get("headlines") or []
    lines.append("Recent headlines:\n" + ("\n".join(f"- {h}" for h in heads[:10]) or "- (none found)"))
    lines.append("Live market events: " + (", ".join(e["label"] for e in live) or "none detected"))
    return "\n".join(lines)


def _agent(role, ev, cfg):
    title, job = ROLES[role]
    extra = ', "size_pct": <number 0-5>' if role == "risk" else ""
    out = claude._ask(AGENT_PROMPT.format(title=title, job=job, evidence=ev, extra=extra), cfg, 450)
    if not out:
        return None
    out["adjust"] = max(-5, min(5, int(out.get("adjust", 0) or 0)))
    out["role"], out["title"] = role, title
    return out


def review(d, live, cfg):
    """Run the six analysts in parallel, then the chair. Returns the desk result or None."""
    ev = evidence(d, live)
    with cf.ThreadPoolExecutor(max_workers=6) as pool:
        views = [v for v in pool.map(lambda r: _agent(r, ev, cfg), ROLES) if v]
    if len(views) < 3:
        return None
    txt = "\n".join(f"- {v['title']} ({v['stance']}, {v['adjust']:+d}): {v['headline']} | "
                    + "; ".join(v.get("reasons", [])[:3]) for v in views)
    chair = claude._ask(CHAIR_PROMPT.format(evidence=ev, views=txt, score=d["score"]), cfg, 400)
    if not chair:
        return None
    chair["adjust"] = max(-15, min(15, int(chair.get("adjust", 0) or 0)))
    return {"views": views, "chair": chair}


def run(cands, live, cfg, log=print):
    """Review each candidate (in parallel, a few at a time). Sets d['desk'], d['score_rules'], d['score']."""
    if not claude.enabled(cfg):
        log("    desk is off (no ANTHROPIC_API_KEY)")
        return False
    with cf.ThreadPoolExecutor(max_workers=cfg.get("desk_parallel", 3)) as pool:
        results = list(pool.map(lambda d: review(d, live, cfg), cands))
    for d, r in zip(cands, results):
        if not r:
            continue
        d["desk"] = r
        d["score_rules"] = d["score"]
        d["score"] = max(0, min(100, d["score"] + r["chair"]["adjust"]))
        d.setdefault("reasons", []).append(
            f"Desk: {r['chair']['call']} ({r['chair']['adjust']:+d}) - {r['chair'].get('memo', '')}")
    log(f"    desk reviewed {sum(1 for d in cands if d.get('desk'))} of {len(cands)} names "
        f"({claude.USAGE['calls']} Claude calls, {claude.USAGE['input_tokens']:,} in / "
        f"{claude.USAGE['output_tokens']:,} out tokens so far)")
    return True


def summary(cands):
    """One line per agent for the 'desk today' strip, built from the reviews (no extra calls)."""
    out = []
    reviewed = [d for d in cands if d.get("desk")]
    for role, (title, _) in list(ROLES.items()) + [("chair", ("Portfolio manager", ""))]:
        if role == "chair":
            calls = [d["desk"]["chair"]["call"] for d in reviewed]
            if calls:
                out.append((title, f"{calls.count('Buy')} Buy, {calls.count('Watch')} Watch, "
                                   f"{calls.count('Pass')} Pass out of {len(calls)} reviewed"))
            continue
        vs = [(d["ticker"], v) for d in reviewed for v in d["desk"]["views"] if v["role"] == role]
        if not vs:
            continue
        bear = sum(1 for _, v in vs if v["stance"] == "bearish")
        t, top = max(vs, key=lambda x: abs(x[1]["adjust"]))
        out.append((title, f"{bear} of {len(vs)} bearish · strongest view on {t}: {top['headline']}"))
    return out


def exits(paper_rows, store, live, details, cfg, log=print):
    """Daily check of open paper picks. Uses Claude if available, else simple rules."""
    alerts = []
    use_ai = claude.enabled(cfg)
    rows = paper_rows[: cfg.get("exit_max", 40)]

    def one(r):
        price = store.latest(r["ticker"])
        if price is None or not r.get("entry"):
            return None
        entry = float(r["entry"])
        ret = price / entry - 1
        if use_ai:
            heads = "\n".join(f"- {n['headline']}" for n in details.news(r["ticker"], 3)[:6]) or "- (none)"
            out = claude._ask(EXIT_PROMPT.format(
                ticker=r["ticker"], kind=r["type"], date=r["date"], entry=entry, price=price, ret=ret,
                reason=r.get("reason", ""), trigger=r.get("exit_trigger", "not recorded"),
                events=", ".join(e["label"] for e in live) or "none", headlines=heads), cfg, 150)
            if out and out.get("action") in ("hold", "trim", "sell"):
                return {"ticker": r["ticker"], "type": r["type"], "ret": ret, "action": out["action"],
                        "why": out.get("why", ""), "source": "desk"}
            return None
        if ret <= -cfg.get("stop_loss", 0.25):
            return {"ticker": r["ticker"], "type": r["type"], "ret": ret, "action": "sell",
                    "why": f"Down {ret:.0%} from entry: stop-loss hit", "source": "rule"}
        if ret >= cfg.get("take_profit", 0.30):
            return {"ticker": r["ticker"], "type": r["type"], "ret": ret, "action": "trim",
                    "why": f"Up {ret:.0%} from entry: consider taking some profit", "source": "rule"}
        return {"ticker": r["ticker"], "type": r["type"], "ret": ret, "action": "hold",
                "why": "No stop-loss or profit level hit", "source": "rule"}

    with cf.ThreadPoolExecutor(max_workers=4) as pool:
        status = [a for a in pool.map(one, rows) if a]
    alerts = [a for a in status if a["action"] in ("trim", "sell")]
    log(f"    exit monitor: {len(alerts)} alert(s) on {len(rows)} open picks")
    return alerts, {a["ticker"]: a for a in status}
