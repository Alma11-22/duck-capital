"""Daily output: a Duck Capital web page you can open on your phone, plus CSVs."""
import csv
import html
import os

from .score import BUCKET_LABEL

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
"""


def _cls(s):
    return "hi" if s >= 65 else "mid" if s >= 45 else "lo"


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


def write(date, live, drops, warnings, stats, outdir="reports"):
    os.makedirs(outdir, exist_ok=True)
    e = html.escape
    p = [f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
         f"<title>Duck Capital – {e(date)}</title><style>{CSS}</style><main>",
         f"<div class=brand>DUCK CAPITAL</div><h1>Today's events, winners and overreactions.</h1>"
         f"<div class=sub>Daily scan · prices as of close {e(date)} · not investment advice</div>"]
    hit, avg, n = _stat(stats["all"])
    p.append("<div class=kpis>"
             f"<div class=kpi>Live events<b>{len(live)}</b></div>"
             f"<div class=kpi>Rebound candidates<b>{len(drops)}</b></div>"
             f"<div class=kpi>Early warnings<b>{len(warnings)}</b></div>"
             f"<div class=kpi>Paper picks<b>{n}</b></div>"
             f"<div class=kpi>Paper hit rate<b>{hit}</b></div>"
             f"<div class=kpi>Paper avg return<b>{avg}</b></div></div>")

    # --- Events ---
    p.append("<h2>Live events: who wins, who loses</h2>")
    if not live:
        p.append("<div class=meta>No major event detected today.</div>")
    for ev in live:
        conf = ("<span class='pill hi'>market confirms</span>" if ev["confirmed"]
                else "<span class='pill gray'>not confirmed by prices yet</span>")
        heads = "".join(f"<li>{e(h)}</li>" for h in ev["headlines"])
        rows = "".join(
            f"<tr><td><b>{e(w['ticker'])}</b><div class=small>{e(w['kind'].replace('_', '-'))}</div></td>"
            f"<td><span class='pill {_cls(w['score'])}'>{w['score']}</span></td>"
            f"<td>{_pct(w['move'])}</td><td class=small>{e(w.get('psych_label', ''))}</td>"
            f"<td class=small>{e('; '.join(w['reasons'][:3]))}</td></tr>" for w in ev.get("winners", [])[:10])
        losers = ", ".join(sorted(ev.get("loser_tickers", []))) or "–"
        p.append(f"<div class='card event'><div class=top><span class=t>{e(ev['label'])}</span>{conf}</div>"
                 f"<div class=meta>Like: {e(ev['past'])} · playbook losers {_pct(ev['losers_move'])}, "
                 f"winners {_pct(ev['winners_move'])} over 5 days</div><ul>{heads}</ul>"
                 f"<b style='display:block;margin-top:10px'>Winners</b>"
                 f"<table><tr><th>Stock</th><th>Score</th><th>5-day</th><th>Numbers</th><th>Why</th></tr>{rows}</table>"
                 f"<div class=meta><b>Likely losers:</b> {e(losers)} (see rebound list below)</div>"
                 f"<div class=meta><b>Sell when:</b> {e(ev['sell_when'])}</div></div>")

    # --- Early warnings ---
    p.append("<h2>Early warnings: bad news, no big drop yet</h2>")
    if not warnings:
        p.append("<div class=meta>None today.</div>")
    for w in warnings:
        tag = " <span class='pill lo'>watchlist</span>" if w["on_watchlist"] else ""
        items = "".join(f"<li>{e(h)}</li>" for h in w["headlines"] + w["red_flags"])
        p.append(f"<div class=card><div class=top><span class=t>{e(w['ticker'])}{tag}</span>"
                 f"<span class='pill lo'>risk {w['neg_score']}</span></div>"
                 f"<div class=meta>${w['close']:,.2f} · {w['drop']:+.0%} from recent high</div><ul>{items}</ul></div>")

    # --- Rebounds ---
    p.append("<h2>Rebound candidates: sold off, ranked by recovery odds</h2>")
    if not drops:
        p.append("<div class=meta>None today.</div>")
    for d in drops:
        reasons = "".join(f"<li>{e(r)}</li>" for r in d["reasons"])
        heads = "".join(f"<li>{e(h)}</li>" for h in d["headlines"][:3])
        plan = " → ".join(f"${x:,.2f}" for x in d["buy_plan"])
        ev = f" · <b>{e(d['event'])}</b>" if d.get("event") else ""
        thesis = ""
        if d.get("claude"):
            c = d["claude"]
            thesis = (f"<div class=thesis><b>Claude: {e(c.get('verdict', '?'))}</b> "
                      f"({c.get('adjust', 0):+d}) — {e(c.get('thesis', ''))}</div>")
        p.append(
            f"<div class=card><div class=top><span class=t>{e(d['ticker'])} · {e(d['name'])}</span>"
            f"<span class='pill {_cls(d['score'])}'>{d['score']}</span></div>"
            f"<div class=meta>${d['close']:,.2f} · {d['drop']:+.0%} from recent high · "
            f"{e(BUCKET_LABEL[d['bucket']])} · ${d['market_cap_musd']/1000:,.0f}B{ev}</div>"
            f"{'<b>News</b><ul>' + heads + '</ul>' if heads else ''}{_psych(d, e)}"
            f"<b>Why this score</b><ul>{reasons}</ul>"
            f"<div class=meta><b>Similar past cases:</b> {e(', '.join(d['analogs']))}</div>"
            f"<div class=meta><b>Staged buy levels:</b> {plan}</div>"
            f"<div class=meta><b>Thesis breaks if:</b> {e(d['exit_trigger'])}</div>{thesis}</div>")

    # --- Paper portfolio ---
    rh, ra, rn = _stat(stats["rebound"])
    wh, wa, wn = _stat(stats["event_winner"])
    p.append("<h2>Paper portfolio track record</h2><div class=card><table>"
             "<tr><th>Strategy</th><th>Picks</th><th>Hit rate</th><th>Avg return</th></tr>"
             f"<tr><td>Rebounds (buy the overreaction)</td><td>{rn}</td><td>{rh}</td><td>{ra}</td></tr>"
             f"<tr><td>Event winners (buy who benefits)</td><td>{wn}</td><td>{wh}</td><td>{wa}</td></tr>"
             "</table></div></main>")

    page = "".join(p)
    open(f"{outdir}/{date}.html", "w").write(page)
    open(f"{outdir}/latest.html", "w").write(page)

    with open(f"{outdir}/{date}-rebounds.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ticker", "name", "score", "drop", "bucket", "event", "psychology", "psych_label", "close",
                    "market_cap_musd", "buy_plan", "claude_verdict", "reasons"])
        for d in drops:
            w.writerow([d["ticker"], d["name"], d["score"], round(d["drop"], 3), d["bucket"], d.get("event") or "",
                        d.get("psych"), d.get("psych_label"), d["close"], d["market_cap_musd"],
                        " / ".join(map(str, d["buy_plan"])), (d.get("claude") or {}).get("verdict", ""),
                        " | ".join(d["reasons"])])
    with open(f"{outdir}/{date}-event-winners.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["event", "ticker", "kind", "score", "move_5d", "psychology", "psych_label", "close", "reasons"])
        for ev in live:
            for x in ev.get("winners", []):
                w.writerow([ev["label"], x["ticker"], x["kind"], x["score"],
                            None if x["move"] is None else round(x["move"], 3), x.get("psych"),
                            x.get("psych_label"), x["close"], " | ".join(x["reasons"])])
    with open(f"{outdir}/{date}-warnings.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ticker", "neg_score", "drop", "close", "watchlist", "headlines", "sec_red_flags"])
        for x in warnings:
            w.writerow([x["ticker"], x["neg_score"], round(x["drop"], 3), x["close"], x["on_watchlist"],
                        " | ".join(x["headlines"]), " | ".join(x["red_flags"])])
    return f"{outdir}/{date}.html"
