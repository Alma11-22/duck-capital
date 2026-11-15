"""Daily output: an HTML report you can open on your phone, plus CSVs."""
import csv
import html
import os

from .score import BUCKET_LABEL

CSS = """
body{font:15px/1.45 -apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#f7f7f5;color:#1d1d1b}
main{max-width:860px;margin:0 auto;padding:20px}
h1{font-size:22px;margin:0 0 4px} h2{font-size:17px;margin:28px 0 10px}
.sub{color:#6b6b66;font-size:13px}
.kpis{display:flex;gap:10px;flex-wrap:wrap;margin:16px 0}
.kpi{background:#fff;border:1px solid #e6e5e0;border-radius:10px;padding:10px 14px;min-width:120px}
.kpi b{display:block;font-size:20px}
.card{background:#fff;border:1px solid #e6e5e0;border-radius:10px;padding:14px;margin:10px 0}
.top{display:flex;justify-content:space-between;align-items:baseline;gap:8px}
.t{font-weight:700;font-size:16px} .score{font-weight:700;padding:2px 9px;border-radius:999px}
.hi{background:#dcf3e3;color:#145c2e} .mid{background:#fdf1d4;color:#7a5300} .lo{background:#f9dede;color:#8a1f1f}
.warn{background:#f9dede;color:#8a1f1f;padding:2px 8px;border-radius:999px;font-size:12px}
ul{margin:6px 0 0 18px;padding:0} li{margin:2px 0}
.meta{color:#6b6b66;font-size:13px;margin-top:6px}
.thesis{background:#f4f3ef;border-radius:8px;padding:8px 10px;margin-top:8px;font-size:14px}
"""


def _cls(s):
    return "hi" if s >= 65 else "mid" if s >= 45 else "lo"


def write(date, drops, warnings, paper_stats, outdir="reports"):
    os.makedirs(outdir, exist_ok=True)
    e = html.escape
    parts = [f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
             f"<title>Rebound AI - {date}</title><style>{CSS}</style><main>",
             f"<h1>Rebound AI daily scan</h1><div class=sub>Prices as of close {e(date)} · not investment advice</div>"]
    hit = f"{paper_stats['hit_rate']:.0%}" if paper_stats["hit_rate"] is not None else "–"
    avg = f"{paper_stats['avg_return']:+.1%}" if paper_stats["avg_return"] is not None else "–"
    parts.append("<div class=kpis>"
                 f"<div class=kpi>Rebound candidates<b>{len(drops)}</b></div>"
                 f"<div class=kpi>Early warnings<b>{len(warnings)}</b></div>"
                 f"<div class=kpi>Paper picks<b>{paper_stats['n']}</b></div>"
                 f"<div class=kpi>Paper hit rate<b>{hit}</b></div>"
                 f"<div class=kpi>Paper avg return<b>{avg}</b></div></div>")

    parts.append("<h2>Early warnings: bad news, no big drop yet</h2>")
    if not warnings:
        parts.append("<div class=meta>None today.</div>")
    for w in warnings:
        tag = " <span class=warn>watchlist</span>" if w["on_watchlist"] else ""
        items = "".join(f"<li>{e(h)}</li>" for h in w["headlines"] + w["red_flags"])
        parts.append(f"<div class=card><div class=top><span class=t>{e(w['ticker'])}{tag}</span>"
                     f"<span class='score lo'>risk {w['neg_score']}</span></div>"
                     f"<div class=meta>${w['close']:,.2f} · {w['drop']:+.0%} from recent high</div><ul>{items}</ul></div>")

    parts.append("<h2>Rebound candidates: dropped, ranked by recovery odds</h2>")
    if not drops:
        parts.append("<div class=meta>None today.</div>")
    for d in drops:
        reasons = "".join(f"<li>{e(r)}</li>" for r in d["reasons"])
        heads = "".join(f"<li>{e(h)}</li>" for h in d["headlines"][:3])
        plan = " → ".join(f"${p:,.2f}" for p in d["buy_plan"])
        thesis = ""
        if d.get("claude"):
            c = d["claude"]
            thesis = (f"<div class=thesis><b>Claude: {e(c.get('verdict', '?'))}</b> "
                      f"({c.get('adjust', 0):+d}) — {e(c.get('thesis', ''))}</div>")
        parts.append(
            f"<div class=card><div class=top><span class=t>{e(d['ticker'])} · {e(d['name'])}</span>"
            f"<span class='score {_cls(d['score'])}'>{d['score']}</span></div>"
            f"<div class=meta>${d['close']:,.2f} · {d['drop']:+.0%} from recent high · "
            f"{e(BUCKET_LABEL[d['bucket']])} · ${d['market_cap_musd']/1000:,.0f}B</div>"
            f"{'<b>News</b><ul>' + heads + '</ul>' if heads else ''}<b>Why this score</b><ul>{reasons}</ul>"
            f"<div class=meta><b>Similar past cases:</b> {e(', '.join(d['analogs']))}</div>"
            f"<div class=meta><b>Staged buy levels:</b> {plan}</div>"
            f"<div class=meta><b>Thesis breaks if:</b> {e(d['exit_trigger'])}</div>{thesis}</div>")
    parts.append("</main>")
    path = f"{outdir}/{date}.html"
    open(path, "w").write("".join(parts))
    open(f"{outdir}/latest.html", "w").write("".join(parts))

    with open(f"{outdir}/{date}-candidates.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ticker", "name", "score", "drop", "bucket", "close", "market_cap_musd", "buy_plan",
                    "claude_verdict", "reasons"])
        for d in drops:
            w.writerow([d["ticker"], d["name"], d["score"], round(d["drop"], 3), d["bucket"], d["close"],
                        d["market_cap_musd"], " / ".join(map(str, d["buy_plan"])),
                        (d.get("claude") or {}).get("verdict", ""), " | ".join(d["reasons"])])
    with open(f"{outdir}/{date}-warnings.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ticker", "neg_score", "drop", "close", "watchlist", "headlines", "sec_red_flags"])
        for x in warnings:
            w.writerow([x["ticker"], x["neg_score"], round(x["drop"], 3), x["close"], x["on_watchlist"],
                        " | ".join(x["headlines"]), " | ".join(x["red_flags"])])
    return path
