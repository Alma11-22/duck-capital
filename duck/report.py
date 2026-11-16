"""Daily output: a Duck Capital web page you can open on your phone, plus CSVs."""
import csv
import html
from . import table_view as tv
import os

from .score import BUCKET_LABEL

_REV = set()

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;600;700&family=Fraunces:opsz,wght@9..144,400;9..144,600&display=swap');
:root{--ink:#0B100F;--accent:#21ABC9;--accent-ink:#1A5A6E;--sky:#F3F5F4;--line:#E9EDEA;--muted:#5B6462;--bg:#FFFFFF}
body{font:15px/1.5 Archivo,-apple-system,"Segoe UI",Helvetica,Arial,sans-serif;margin:0;background:var(--bg);color:var(--ink)}
main{max-width:880px;margin:0 auto;padding:28px 20px}
h1{font:400 34px/1.1 Fraunces,Georgia,serif;margin:0 0 6px;letter-spacing:-.01em}
h2{font:400 22px/1.2 Fraunces,Georgia,serif;margin:36px 0 12px;padding-top:18px;border-top:1px solid var(--line)}
.brand{font:600 13px Fraunces,Georgia,serif;letter-spacing:.32em;margin-bottom:14px}
.sub{color:var(--muted);font-size:13px}
.kpis{display:flex;gap:10px;flex-wrap:wrap;margin:20px 0}
.kpi{background:var(--sky);border-radius:14px;padding:12px 16px;min-width:110px;font-size:12px;color:var(--muted)}
.kpi b{display:block;font:400 26px Fraunces,Georgia,serif;color:var(--ink);margin-top:2px}
.card{background:#fff;border:1px solid var(--line);border-radius:14px;padding:16px;margin:12px 0}
.event{border-left:4px solid var(--accent)}
.top{display:flex;justify-content:space-between;align-items:baseline;gap:8px;flex-wrap:wrap}
.t{font-weight:700;font-size:16px}
.pill{font-weight:600;padding:3px 11px;border-radius:999px;font-size:13px}
.hi{background:var(--accent);color:#0B100F} .mid{background:var(--sky);color:var(--accent-ink)} .lo{background:#FBE9E9;color:#B3261E}
.gray{background:var(--sky);color:var(--muted)}
ul{margin:6px 0 0 18px;padding:0} li{margin:2px 0}
b{font-weight:600}
.meta{color:var(--muted);font-size:13px;margin-top:6px} .meta b{color:var(--ink)}
.thesis{background:var(--sky);border-radius:10px;padding:10px 12px;margin-top:10px;font-size:14px}
table{width:100%;border-collapse:collapse;font-size:14px;margin-top:8px}
td,th{padding:7px 4px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{color:var(--muted);font-weight:600;font-size:12px}
.meter{height:6px;background:var(--sky);border-radius:3px;overflow:hidden;margin-top:5px;max-width:200px}
.meter i{display:block;height:100%;background:var(--accent)}
.small{font-size:12px;color:var(--muted)}
a{color:var(--accent-ink)}
"""+tv.CSS+""""""


def _cls(s):
    return "hi" if s >= 70 else "mid" if s >= 60 else "gray"


def _pct(x):
    return "–" if x is None else f"{x:+.0%}"


def _psych(d, e):
    if "psych" not in d:
        return ""
    good = "".join(f"<li>{e(x)}</li>" for x in d["numbers_good"])
    bad = "".join(f"<li>{e(x)}</li>" for x in d["numbers_bad"])
    return (f"<div class=meta><b>Psychology vs. fundamentals:</b> {e(d['psych_label'])} ({d['psych']}/100)"
            f"<div class=meter><i style='width:{d['psych']}%'></i></div></div>"
            + (f"<div class=small>The numbers say:</div><ul class=small>{good}{bad}</ul>" if good or bad else ""))


def _stat(s):
    hit = f"{s['hit_rate']:.0%}" if s["hit_rate"] is not None else "–"
    avg = f"{s['avg_return']:+.1%}" if s["avg_return"] is not None else "–"
    return hit, avg, s["n"]


def _rebound_card(d, e):
    reasons = "".join(f"<li>{e(r)}</li>" for r in d["reasons"])
    heads = "".join(f"<li>{e(h)}</li>" for h in d["headlines"][:3])
    plan = " → ".join(f"${x:,.2f}" for x in d["buy_plan"])
    ev = f" · <b>{e(d['event'])}</b>" if d.get("event") else ""
    thesis = _desk_block(d, e)
    return (f"<div class=card{tv.attr(d['ticker'], _REV)}><div class=top><span class=t>{e(d['ticker'])} · {e(d['name'])}"
            f"{tv.tag(d['ticker'], _REV)}</span>"
            f"<span class='pill {_cls(d['score'])}'>{d['score']}</span></div>"
            f"<div class=meta>${d['close']:,.2f} · {d['drop']:+.0%} from recent high · "
            f"{e(BUCKET_LABEL[d['bucket']])} · ${d['market_cap_musd']/1000:,.0f}B{ev}</div>"
            f"{'<b>News</b><ul>' + heads + '</ul>' if heads else ''}{_psych(d, e)}"
            f"<b>Why this score</b><ul>{reasons}</ul>"
            f"<div class=meta><b>Similar past cases:</b> {e(', '.join(d['analogs']))}</div>"
            f"<div class=meta><b>Staged buy levels:</b> {plan}</div>"
            f"<div class=meta><b>Thesis breaks if:</b> {e(d['exit_trigger'])}</div>{thesis}</div>")


ICON = {"bullish": "▲", "neutral": "●", "bearish": "▼"}


def _desk_block(d, e):
    k = d.get("desk")
    if not k:
        return ""
    c = k["chair"]
    pill = {"Buy": "hi", "Watch": "mid", "Pass": "lo"}.get(c.get("call"), "gray")
    votes = "".join(f"<li><b>{e(v['title'])}</b> {ICON.get(v['stance'], '')} {e(v['stance'])} "
                    f"({v['adjust']:+d}): {e(v['headline'])}</li>" for v in k["views"])
    dis = f"<div class=small><b>Disagreement:</b> {e(c['disagreement'])}</div>" if c.get("disagreement") else ""
    return (f"<div class=thesis><b>The desk:</b> <span class='pill {pill}'>{e(c.get('call', '?'))}</span> "
            f"rules {d.get('score_rules', d['score'])} → desk {d['score']}<div style=margin-top:6px>{e(c.get('memo', ''))}</div>"
            f"{dis}<ul class=small>{votes}</ul></div>")


def _call(d):
    k = d.get("desk")
    return k["chair"].get("call", "") if k else ""


def _main_reason(d):
    bits = [f"{d['drop']:+.0%} on {BUCKET_LABEL[d['bucket']].lower()} news"]
    if d.get("psych_label") in ("Mostly psychology", "Mostly fundamentals"):
        bits.append(d["psych_label"].lower())
    extra = [r for r in d["reasons"][1:] if not r.startswith(("Deep drop", "Numbers still", "The numbers"))]
    if extra:
        bits.append(extra[0].lower())
    return "; ".join(bits)


HOW = """<h2>How to read the score (0–100)</h2><div class=card>
<p style=margin-top:0>It starts from history: how often past selloffs of the same kind recovered. Then it adjusts.
Insiders buying, analysts upgrading and healthy numbers push it up. Heavy debt, SEC red flags and missed earnings
pull it down.</p>
<p><span class='pill hi'>70+ Buy</span> &nbsp;The paper portfolio buys in three steps (now, −10%, −20%).</p>
<p><span class='pill mid'>60–69 Watch</span> &nbsp;Interesting, but not yet.</p>
<p><span class='pill gray'>Under 60</span> &nbsp;Not shown.</p>
<p><b>Psychology meter:</b> is the drop about mood or numbers? High means the business still looks fine and the price
fell anyway.</p>
<p><b>Sector selloff:</b> the stock fell together with its whole sector, with no bad news of its own. A sector
<i>panic</i> (numbers still healthy) has recovered about 70% of the time; a sector <i>downturn</i> (numbers weakening)
about 35%; crypto about 40%. Small samples are weighted toward the 40% average.</p>
<p><b>The desk:</b> six Claude analysts (news, fundamentals, bear, historian, event, risk) review the top names,
then a portfolio-manager agent makes the call and can move the score by at most 15 points. The track record keeps
"rules only" and "rules + desk" apart so you can see whether the desk adds value.</p>
<p style=margin-bottom:0><b>Before the move:</b> news that matters, price hasn't reacted yet. Not a buy signal on its
own; it's your head start.</p></div>"""


def write(date, live, drops, before, stats, all_drops=None, warnings=None, outdir="reports",
          desk_today=(), desk_on=False, exit_alerts=(), desk_error="", exit_status=None):
    """drops: rebounds to show (already filtered). all_drops/warnings: full lists for the CSVs."""
    os.makedirs(outdir, exist_ok=True)
    all_drops = drops if all_drops is None else all_drops
    warnings = warnings or []
    e = html.escape
    modal, reviewed = tv.block(list(all_drops) + [w for ev in live for w in ev.get("winners", [])], exit_status or {})
    _REV.clear()
    _REV.update(reviewed)
    SECT = ("sector_panic", "sector_downturn", "crypto_selloff")
    company = [d for d in drops if d["bucket"] not in SECT]
    buy = [d for d in company if d["score"] >= 70]
    watch = [d for d in company if d["score"] < 70]
    groups = {}
    for d in all_drops:
        if d["bucket"] in SECT and d.get("sector_info"):
            groups.setdefault(d["sector_info"]["sector"], []).append(d)
    groups = sorted(groups.items(), key=lambda kv: -len(kv[1]))
    p = [f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
         f"<title>Duck Capital – {e(date)}</title><style>{CSS}</style><main>",
         f"<div class=brand>DUCK CAPITAL</div><h1>Today's events, winners and overreactions.</h1>"
         f"<div class=sub>Daily scan · prices as of close {e(date)} · not investment advice</div>"]
    hit, avg, n = _stat(stats["all"])
    p.append("<div class=kpis>"
             f"<div class=kpi>Live events<b>{len(live)}</b></div>"
             f"<div class=kpi>Before the move<b>{len(before)}</b></div>"
             f"<div class=kpi>Sector selloffs<b>{sum(len(v) for _, v in groups)}</b></div>"
             f"<div class=kpi>Buy<b>{len(buy)}</b></div>"
             f"<div class=kpi>Watch<b>{len(watch)}</b></div>"
             f"<div class=kpi>Paper hit rate<b>{hit}</b></div>"
             f"<div class=kpi>Paper avg return<b>{avg}</b></div></div>")

    # --- The desk today ---
    if desk_on and desk_today:
        rows = "".join(f"<tr><td><b>{e(t)}</b></td><td class=small>{e(x)}</td></tr>" for t, x in desk_today)
        p.append(f"<h2>The desk today</h2><div class=card><table>{rows}</table></div>")
    elif not desk_on:
        p.append("<div class=meta>The desk (analyst agents) is off: add ANTHROPIC_API_KEY to turn it on.</div>")
    elif desk_error:
        p.append(f"<div class=meta><b>The desk couldn't run today:</b> {e(desk_error)}</div>")

    # --- Exit alerts ---
    if exit_alerts:
        rows = "".join(f"<tr><td><b>{e(a['ticker'])}</b><div class=small>{e(a['type'].replace('_', ' '))}</div></td>"
                       f"<td><span class='pill {'lo' if a['action'] == 'sell' else 'mid'}'>{e(a['action'])}</span></td>"
                       f"<td>{a['ret']:+.0%}</td><td class=small>{e(a['why'])}</td></tr>" for a in exit_alerts)
        p.append(f"<h2>Exit alerts: open picks to sell or trim</h2><div class=card><table><tr><th>Pick</th>"
                 f"<th>Action</th><th>Since buy</th><th>Why</th></tr>{rows}</table></div>")

    # --- Top 5 ---
    top = [(d["score"], d["ticker"], _main_reason(d) + (f"; desk says {_call(d)}" if _call(d) else ""),
            "Buy" if d["score"] >= 70 else "Watch") for d in drops]
    for ev in live:
        for w in ev.get("winners", []):
            if w["score"] >= 60:
                top.append((w["score"], w["ticker"], f"benefits from {ev['label'].lower()}; {_pct(w['move'])} over 5 days",
                            "Buy" if w["score"] >= 70 else "Watch"))
    seen, rows = set(), []
    for s, t, why, act in sorted(top, key=lambda x: -x[0]):
        if t in seen:
            continue
        seen.add(t)
        rows.append(f"<tr{tv.attr(t, _REV)}><td><b>{e(t)}</b>{tv.tag(t, _REV)}</td><td><span class='pill {_cls(s)}'>{s}</span></td>"
                    f"<td>{act}</td><td class=small>{e(why)}</td></tr>")
        if len(rows) == 5:
            break
    p.append("<h2>Top 5 today</h2>" + (f"<div class=card><table><tr><th>Stock</th><th>Score</th><th></th>"
             f"<th>Main reason</th></tr>{''.join(rows)}</table></div>" if rows else "<div class=meta>Nothing scores 60+ today.</div>"))

    # --- Before the move ---
    p.append("<h2>Before the move: news that matters, price hasn't reacted</h2>")
    if not before:
        p.append("<div class=meta>Nothing today.</div>")
    for b in before:
        tag = " <span class='pill gray'>watchlist</span>" if b["on_watchlist"] else ""
        pill = {"bad": "<span class='pill lo'>looks bad for the stock</span>",
                "good": "<span class='pill hi'>looks good for the stock</span>",
                "mixed": "<span class='pill mid'>mixed</span>"}[b["direction"]]
        items = "".join(f"<li>{e(h)}</li>" for h in b["headlines"][:3] + b["red_flags"])
        mv = f"{_pct(b['move'])} over 5 days" if b["move"] is not None else ""
        hi = f" · {b['drop']:+.0%} from recent high" if b.get("drop") is not None else ""
        p.append(f"<div class=card><div class=top><span class=t>{e(b['ticker'])}{tag}</span>{pill}</div>"
                 f"<div class=meta>${b['close']:,.2f} · price so far: {mv}{hi}</div>"
                 f"<div class=meta><b>What happened:</b> {e('; '.join(dict.fromkeys(b['why'])))}</div>"
                 + (f"<ul>{items}</ul>" if items else "") + "</div>")

    # --- Events ---
    p.append("<h2>Live events: who wins, who loses</h2>")
    if not live:
        p.append("<div class=meta>No major event detected today.</div>")
    for ev in live:
        conf = ("<span class='pill hi'>market confirms</span>" if ev["confirmed"]
                else "<span class='pill gray'>not confirmed by prices yet</span>")
        heads = "".join(f"<li>{e(h)}</li>" for h in ev["headlines"])
        wrows = "".join(
            f"<tr{tv.attr(w['ticker'], _REV)}><td><b>{e(w['ticker'])}</b>{tv.tag(w['ticker'], _REV)}<div class=small>{e(w['kind'].replace('_', '-'))}</div></td>"
            f"<td><span class='pill {_cls(w['score'])}'>{w['score']}</span></td>"
            f"<td>{_pct(w['move'])}</td><td class=small>{e(w.get('psych_label', ''))}</td>"
            f"<td class=small>{('<b>Desk: ' + e(_call(w)) + '.</b> ' + e(w['desk']['chair'].get('memo', ''))) if w.get('desk') else e('; '.join(w['reasons'][:3]))}</td></tr>"
            for w in ev.get("winners", [])[:8])
        losers = ", ".join(sorted(ev.get("loser_tickers", []))) or "–"
        p.append(f"<div class='card event'><div class=top><span class=t>{e(ev['label'])}</span>{conf}</div>"
                 f"<div class=meta>Like: {e(ev['past'])} · playbook losers {_pct(ev['losers_move'])}, "
                 f"winners {_pct(ev['winners_move'])} over 5 days</div>"
                 + (f"<div class=meta><b>Spotted in prices:</b> the stocks this kind of event hurts are "
                    f"{_pct(ev['month_gap'])} vs. the market over the past month</div>" if ev.get("price_seen") else "")
                 + f"<ul>{heads}</ul>"
                 f"<b style='display:block;margin-top:10px'>Who benefits</b>"
                 f"<table><tr><th>Stock</th><th>Score</th><th>5-day</th><th>Numbers</th><th>Why</th></tr>{wrows}</table>"
                 f"<div class=meta><b>Who gets hurt:</b> {e(losers)}</div>"
                 f"<div class=meta><b>Sell when:</b> {e(ev['sell_when'])}</div></div>")

    # --- Sector selloffs ---
    p.append("<h2>Sector selloffs: fell with the whole sector</h2>")
    if not groups:
        p.append("<div class=meta>None today.</div>")
    for name, ds in groups:
        ds = sorted(ds, key=lambda x: -x["score"])
        sd = ds[0]["sector_info"]["sector_drop"]
        kinds = {b: sum(1 for d in ds if d["bucket"] == b) for b in SECT}
        kind = ("Crypto selloff: past cases recovered about 40% of the time" if kinds["crypto_selloff"] else
                f"{kinds['sector_panic']} look like panic (numbers still healthy), "
                f"{kinds['sector_downturn']} like a real downturn (numbers weakening)")
        rows = "".join(
            f"<tr{tv.attr(d['ticker'], _REV)}><td><b>{e(d['ticker'])}</b>{tv.tag(d['ticker'], _REV)}<div class=small>{e(d['name'][:28])}</div></td>"
            f"<td><span class='pill {_cls(d['score'])}'>{d['score']}</span></td><td>{d['drop']:+.0%}</td>"
            f"<td class=small>{e(BUCKET_LABEL[d['bucket']])}</td><td class=small>{e(d.get('psych_label', ''))}</td>"
            f"<td class=small>{e(_call(d))}</td></tr>"
            for d in ds[:5])
        p.append(f"<div class='card event'><div class=top><span class=t>{e(name)}</span>"
                 f"<span class='pill gray'>{len(ds)} stocks</span></div>"
                 f"<div class=meta>Sector {sd:+.0%} from its 1-month high · {e(kind)}</div>"
                 f"<b style='display:block;margin-top:10px'>Best 5</b>"
                 f"<table><tr><th>Stock</th><th>Score</th><th>Drop</th><th>Kind</th><th>Numbers</th><th>Desk</th></tr>{rows}</table></div>")

    # --- Company-specific Buy / Watch ---
    p.append(f"<h2>Buy (70+): fell on its own news, strong recovery odds</h2>")
    p.extend([_rebound_card(d, e) for d in buy] or ["<div class=meta>None today.</div>"])
    p.append(f"<h2>Watch (60–69): fell on its own news, not yet</h2>")
    p.extend([_rebound_card(d, e) for d in watch] or ["<div class=meta>None today.</div>"])
    hidden = len([d for d in all_drops if d["bucket"] not in SECT]) - len(company)
    repo = os.environ.get("GITHUB_REPOSITORY", "Alma11-22/duck-capital")
    csv_url = f"https://github.com/{repo}/blob/main/reports/{date}-rebounds.csv"
    if hidden:
        p.append(f"<div class=meta>{hidden} smaller or lower-scoring drops hidden; they're in the "
                 f"<a href='{e(csv_url)}'>full download</a>.</div>")

    p.append(HOW)

    # --- Paper portfolio ---
    rh, ra, rn = _stat(stats["rebound"])
    wh, wa, wn = _stat(stats["event_winner"])
    p.append("<h2>Paper portfolio track record</h2><div class=card><table>"
             "<tr><th>Strategy</th><th>Picks</th><th>Hit rate</th><th>Avg return</th></tr>"
             f"<tr><td>Rebounds (buy the overreaction)</td><td>{rn}</td><td>{rh}</td><td>{ra}</td></tr>"
             f"<tr><td>Event winners (buy who benefits)</td><td>{wn}</td><td>{wh}</td><td>{wa}</td></tr>"
             + ("<tr><td><b>Rules only</b> (both of the above)</td><td>{2}</td><td>{0}</td><td>{1}</td></tr>".format(*_stat(stats["rules"]))
                if "rules" in stats else "")
             + ("<tr><td><b>Rules + desk</b> (chair says Buy)</td><td>{2}</td><td>{0}</td><td>{1}</td></tr>".format(*_stat(stats["desk"]))
                if "desk" in stats else "")
             + "</table></div></main>" + modal)

    page = "".join(p)
    open(f"{outdir}/{date}.html", "w").write(page)
    open(f"{outdir}/latest.html", "w").write(page)

    with open(f"{outdir}/{date}-rebounds.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ticker", "name", "score", "drop", "bucket", "event", "psychology", "psych_label", "close",
                    "market_cap_musd", "buy_plan", "desk_call", "sector", "sector_drop", "reasons"])
        for d in all_drops:
            w.writerow([d["ticker"], d["name"], d["score"], round(d["drop"], 3), d["bucket"], d.get("event") or "",
                        d.get("psych"), d.get("psych_label"), d["close"], d["market_cap_musd"],
                        " / ".join(map(str, d["buy_plan"])), _call(d),
                        (d.get("sector_info") or {}).get("sector", ""),
                        (d.get("sector_info") or {}).get("sector_drop", ""), " | ".join(d["reasons"])])
    with open(f"{outdir}/{date}-event-winners.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["event", "ticker", "kind", "score", "move_5d", "psychology", "psych_label", "close", "reasons"])
        for ev in live:
            for x in ev.get("winners", []):
                w.writerow([ev["label"], x["ticker"], x["kind"], x["score"],
                            None if x["move"] is None else round(x["move"], 3), x.get("psych"),
                            x.get("psych_label"), x["close"], " | ".join(x["reasons"])])
    with open(f"{outdir}/{date}-before-the-move.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ticker", "direction", "move_5d", "close", "watchlist", "what_happened", "headlines"])
        for b in before:
            w.writerow([b["ticker"], b["direction"], None if b["move"] is None else round(b["move"], 3), b["close"],
                        b["on_watchlist"], " | ".join(b["why"]), " | ".join(b["headlines"] + b["red_flags"])])
    with open(f"{outdir}/{date}-warnings.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ticker", "neg_score", "drop", "close", "watchlist", "headlines", "sec_red_flags"])
        for x in warnings:
            w.writerow([x["ticker"], x["neg_score"], round(x["drop"], 3), x["close"], x["on_watchlist"],
                        " | ".join(x["headlines"]), " | ".join(x["red_flags"])])
    return f"{outdir}/{date}.html"
