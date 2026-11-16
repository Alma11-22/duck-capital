"""Optional Claude layer (only runs if ANTHROPIC_API_KEY is set).

1. review():       temporary scare or real damage? Moves a rebound score by up to +/-15.
2. event_ideas():  for a live event, suggests extra winners the playbook missed,
                   especially second-order ones.
"""
import json
import os
import threading
import urllib.request

USAGE = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "errors": 0, "last_error": ""}
_U = threading.Lock()


def enabled(cfg):
    return bool(os.environ.get("ANTHROPIC_API_KEY")) and cfg.get("use_claude")

REVIEW_PROMPT = """You are a skeptical equity analyst. A stock sold off on bad news.
Decide whether the damage is TEMPORARY (sentiment, fixable, or overblown) or REAL
(the business's earnings power is impaired). Use only the evidence given.

Stock: {name} ({ticker}), {industry}
Down {drop:.0%} from its {lookback}-day high. Kind of news: {bucket}.
Recent headlines:
{headlines}
Hard checks: {checks}
Most similar past cases: {analogs}

Reply with JSON only:
{{"verdict": "temporary" | "real" | "unclear",
  "adjust": <integer -15..15 to add to the score>,
  "thesis": "<2-3 sentences: why, and what would prove you wrong>"}}"""

IDEAS_PROMPT = """A market event is unfolding: {label}.
Headlines:
{headlines}
Stocks already on our winners list: {known}

Name up to 6 OTHER US-listed stocks likely to BENEFIT, favouring second-order,
less obvious beneficiaries (suppliers, substitutes, companies that gain share).
Only real, currently listed tickers you are confident about.

Reply with JSON only: {{"ideas": [{{"ticker": "XXX", "why": "<one short line>"}}]}}"""


def _ask(prompt, cfg, max_tokens=500):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key or not cfg.get("use_claude"):
        return None
    body = {"model": cfg["claude_model"], "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                                 headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                                          "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            resp = json.loads(r.read())
        text = resp["content"][0]["text"]
        with _U:
            USAGE["calls"] += 1
            USAGE["input_tokens"] += resp.get("usage", {}).get("input_tokens", 0)
            USAGE["output_tokens"] += resp.get("usage", {}).get("output_tokens", 0)
        return json.loads(text[text.find("{"): text.rfind("}") + 1])
    except Exception as e:  # never let the optional layer break the run
        msg = str(e)
        body = getattr(e, "read", None)
        if body:
            try:
                msg += " - " + json.loads(body()).get("error", {}).get("message", "")
            except Exception:
                pass
        with _U:
            USAGE["errors"] += 1
            USAGE["last_error"] = msg
        print(f"  ! Claude call failed: {msg}")
        return None


def review(stock, news, result, cfg):
    heads = "\n".join(f"- {n['headline']}" for n in news[:12]) or "- (no headlines found)"
    out = _ask(REVIEW_PROMPT.format(
        name=stock["name"], ticker=stock["ticker"], industry=stock["industry"], drop=-stock["drop"],
        lookback=cfg["lookback_days"], bucket=stock["bucket"], headlines=heads,
        checks="; ".join(result["reasons"]), analogs=", ".join(result["analogs"])), cfg, 400)
    if out:
        out["adjust"] = max(-15, min(15, int(out.get("adjust", 0))))
    return out


def event_ideas(event, known, cfg):
    heads = "\n".join(f"- {h}" for h in event["headlines"]) or "- (none)"
    out = _ask(IDEAS_PROMPT.format(label=event["label"], headlines=heads, known=", ".join(sorted(known))), cfg)
    if not out:
        return []
    return [(i["ticker"].upper().strip(), i.get("why", "")) for i in out.get("ideas", [])
            if i.get("ticker") and i["ticker"].upper() not in known][:6]
