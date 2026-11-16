"""The 'desk table' view: tap a stock, see its desk around a round table.

Pure HTML/CSS/JS, embedded in the daily page. Data comes from the desk reviews (no extra calls).
"""
import html
import json

SEATS = [  # role, label, short, position (left %, top %) around an oval table
    ("chair", "Portfolio manager", "PM", 50, 9),
    ("news", "News analyst", "NEWS", 17, 27),
    ("fundamentals", "Fundamentals", "FUND", 13, 50),
    ("bear", "Bear", "BEAR", 17, 73),
    ("historian", "Historian", "HIST", 83, 27),
    ("event", "Event strategist", "EVENT", 87, 50),
    ("risk", "Risk manager", "RISK", 83, 73),
    ("exit", "Exit monitor", "EXIT", 50, 90),
]

CSS = """
.deskable{cursor:pointer}
.deskable:hover{outline:2px solid var(--accent);outline-offset:2px;border-radius:8px}
.desk-tag{display:inline-block;font-size:11px;letter-spacing:.06em;color:var(--accent-ink);background:#E3F4F8;
  border-radius:999px;padding:2px 8px;margin-left:6px;vertical-align:middle;font-weight:600}
#dm{position:fixed;inset:0;background:rgba(11,16,15,.55);display:none;z-index:50;overflow:auto}
#dm.on{display:block}
#dm .box{background:#fff;max-width:620px;margin:24px auto;border-radius:18px;padding:18px 18px 22px;position:relative}
#dm .x{position:absolute;right:12px;top:10px;border:0;background:none;font-size:26px;cursor:pointer;color:var(--muted)}
#dm h3{font-family:Fraunces,Georgia,serif;font-weight:600;margin:2px 0 2px;font-size:22px}
#dm .sub{color:var(--muted);font-size:13px;margin-bottom:6px}
.tbl{position:relative;width:100%;aspect-ratio:1/1.25;max-width:520px;margin:14px auto 0}
.oval{position:absolute;left:30%;right:30%;top:19%;bottom:19%;border-radius:50%;
  background:radial-gradient(ellipse at 50% 40%,#F3F5F4,#E4EBE8);border:2px solid var(--line)}
.center{position:absolute;left:31%;right:31%;top:34%;bottom:34%;display:flex;flex-direction:column;
  align-items:center;justify-content:center;text-align:center;gap:6px}
.center .call{font-family:Fraunces,Georgia,serif;font-size:24px;font-weight:600}
.center .sc{font-size:13px;color:var(--muted)}
.seat{position:absolute;transform:translate(-50%,-28px);width:84px;text-align:center;border:0;background:none;
  cursor:pointer;padding:0;font:inherit}
.seat .dot{width:48px;height:48px;border-radius:50%;margin:0 auto 3px;display:flex;align-items:center;
  justify-content:center;font-size:11px;font-weight:700;letter-spacing:.04em;color:#fff;
  box-shadow:0 2px 6px rgba(0,0,0,.12);border:3px solid #fff}
.seat .nm{font-size:11px;line-height:1.15;color:var(--ink)}
.seat.sel .dot{outline:3px solid var(--accent);outline-offset:2px}
.seat.empty .dot{background:#fff;border:2px dashed #C9D2CF;color:#9AA5A2;box-shadow:none}
.bull{background:#2E9E6B}.neut{background:#8A9592}.bear{background:#D0583F}.chair{background:var(--accent-ink)}
.hold{background:#2E9E6B}.trim{background:#D9A23B}.sell{background:#D0583F}
.panel{border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin-top:12px;background:var(--sky)}
.panel b.t{font-family:Fraunces,Georgia,serif;font-size:17px}
.panel ul{margin:6px 0 0 18px;padding:0}
.legend{margin-top:16px!important;display:flex;gap:12px;flex-wrap:wrap;font-size:12px;color:var(--muted);justify-content:center;margin-top:8px}
.legend i{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:4px;vertical-align:-1px}
"""

JS = r"""
(function(){
const D=window.DESK||{};const S=window.SEATS;const m=document.getElementById('dm');
const cls={bullish:'bull',neutral:'neut',bearish:'bear'};
const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function panel(d,role){
  const p=m.querySelector('.panel');
  if(role==='chair'){p.innerHTML=`<b class=t>Portfolio manager: ${esc(d.call)}</b><div style=margin-top:4px>${esc(d.memo)}</div>`+
     (d.disagreement?`<div class=small style=margin-top:6px><b>Where they disagreed:</b> ${esc(d.disagreement)}</div>`:'');return;}
  if(role==='exit'){ if(!d.exit){p.innerHTML='<b class=t>Exit monitor</b><div>Not in the paper portfolio yet, so nothing to exit.</div>';return;}
     p.innerHTML=`<b class=t>Exit monitor: ${esc(d.exit.action)}</b><div>${esc(d.exit.why)}</div><div class=small>Since paper buy: ${(d.exit.ret*100).toFixed(1)}%</div>`;return;}
  const v=d.views[role]; if(!v){p.innerHTML='<div>No view from this agent.</div>';return;}
  p.innerHTML=`<b class=t>${esc(v.title)}: ${esc(v.stance)} (${v.adjust>0?'+':''}${v.adjust})</b><div style=margin-top:4px>${esc(v.headline)}</div>`+
    (v.reasons&&v.reasons.length?'<ul>'+v.reasons.map(r=>`<li>${esc(r)}</li>`).join('')+'</ul>':'')+
    (v.size_pct!=null?`<div class=small style=margin-top:4px><b>Suggested size:</b> ${esc(v.size_pct)}% of portfolio</div>`:'');
}
function open(t){
  const d=D[t]; if(!d) return;
  m.querySelector('h3').textContent=(d.name&&d.name!==t)?t+' · '+d.name:t;
  m.querySelector('.sub').textContent=d.sub;
  const box=m.querySelector('.tbl'); let h='<div class=oval></div>';
  h+=`<div class=center><div class="pill ${d.call==='Buy'?'hi':d.call==='Watch'?'mid':'lo'}">desk call</div>
      <div class=call>${esc(d.call)}</div><div class=sc>rules ${d.rules} → desk ${d.score}</div></div>`;
  S.forEach(([role,label,short,x,y])=>{
    let c='',empty=false;
    if(role==='chair') c='chair';
    else if(role==='exit'){ if(d.exit) c=d.exit.action; else empty=true; }
    else { const v=d.views[role]; c=v?cls[v.stance]||'neut':''; if(!v) empty=true; }
    h+=`<button class="seat${empty?' empty':''}" data-role=${role} style="left:${x}%;top:${y}%">
        <div class="dot ${c}">${short}</div><div class=nm>${label}</div></button>`;
  });
  box.innerHTML=h;
  box.querySelectorAll('.seat').forEach(b=>b.onclick=()=>{box.querySelectorAll('.seat').forEach(z=>z.classList.remove('sel'));
     b.classList.add('sel');panel(d,b.dataset.role);});
  box.querySelector('[data-role=chair]').classList.add('sel'); panel(d,'chair');
  m.classList.add('on'); document.body.style.overflow='hidden';
}
function close(){m.classList.remove('on');document.body.style.overflow='';}
m.querySelector('.x').onclick=close; m.onclick=e=>{if(e.target===m)close();};
document.addEventListener('keydown',e=>{if(e.key==='Escape')close();});
document.querySelectorAll('[data-desk]').forEach(el=>{el.classList.add('deskable');el.addEventListener('click',ev=>{
  if(ev.target.closest('a'))return; open(el.dataset.desk);});});
})();
"""

MODAL = """<div id=dm role=dialog aria-modal=true><div class=box><button class=x aria-label=Close>×</button>
<h3></h3><div class=sub></div><div class=tbl></div>
<div class=legend><span><i class=bull></i>bullish</span><span><i class=neut></i>neutral</span>
<span><i class=bear></i>bearish</span><span><i style="background:#fff;border:2px dashed #C9D2CF"></i>no seat today</span></div>
<div class=panel></div><div class=small style="margin-top:10px;color:var(--muted)">Tap a seat to see what that agent thinks.
The desk advises; you decide.</div></div></div>"""


def payload(stocks, exit_status):
    """Data for every stock the desk reviewed."""
    out = {}
    for d in stocks:
        k = d.get("desk")
        if not k:
            continue
        c = k["chair"]
        drop = f"{d['drop']:+.0%} from recent high · " if d.get("drop") is not None else ""
        evt = f"benefits from {d['event_label']} · " if d.get("event_label") else ""
        out[d["ticker"]] = {
            "name": d.get("name", d["ticker"]),
            "sub": f"${d['close']:,.2f} · {drop}{evt}desk reviewed",
            "call": c.get("call", "?"), "memo": c.get("memo", ""), "disagreement": c.get("disagreement", ""),
            "rules": d.get("score_rules", d["score"]), "score": d["score"],
            "views": {v["role"]: {k2: v.get(k2) for k2 in ("title", "stance", "adjust", "headline", "reasons", "size_pct")}
                      for v in k["views"]},
            "exit": exit_status.get(d["ticker"]),
        }
    return out


def block(stocks, exit_status):
    data = payload(stocks, exit_status)
    if not data:
        return "", set()
    js_data = json.dumps(data).replace("</", "<\\/")
    seats = json.dumps([[r, l, s, x, y] for r, l, s, x, y in SEATS])
    return (MODAL + f"<script>window.DESK={js_data};window.SEATS={seats};</script><script>{JS}</script>",
            set(data))


def tag(ticker, reviewed):
    return f" <span class=desk-tag>DESK ▸</span>" if ticker in reviewed else ""


def attr(ticker, reviewed):
    return f" data-desk='{html.escape(ticker)}'" if ticker in reviewed else ""
