"""Optional Claude layer (only runs if ANTHROPIC_API_KEY is set).

1. review():       temporary scare or real damage? Moves a rebound score by up to +/-15.
2. event_ideas():  for a live event, suggests extra winners the playbook missed,
                   especially second-order ones.
"""
import json
import os
import threading
import time
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


def _parse(text):
    """First complete JSON object in the reply (tolerates prose or code fences around it)."""
    dec = json.JSONDecoder()
    i = text.find("{")
    while i != -1:
        try:
            obj, _ = dec.raw_decode(text[i:])
            if isinstance(obj, dict):
                return obj
        except ValueError:
            pass
        i = text.find("{", i + 1)
    raise ValueError("no JSON object in reply")


def _ask(prompt, cfg, max_tokens=500, _tries=3):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key or not cfg.get("use_claude"):
        return None
    last = ""
    for attempt in range(_tries):
        body = {"model": cfg["claude_model"], "max_tokens": max_tokens,
                "system": "You answer with one JSON object only. No text before or after it, no code fences.",
                "messages": [{"role": "user", "content": prompt}]}
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                                     headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                                              "content-type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                resp = json.loads(r.read())
            with _U:
                USAGE["calls"] += 1
                USAGE["input_tokens"] += resp.get("usage", {}).get("input_tokens", 0)
                USAGE["output_tokens"] += resp.get("usage", {}).get("output_tokens", 0)
            text = "".join(c.get("text", "") for c in resp.get("content", []) if c.get("type") == "text")
            try:
                return _parse(text)
            except ValueError:
                last = ("reply was cut off" if resp.get("stop_reason") == "max_tokens" else "reply wasn't JSON")
                max_tokens = int(max_tokens * 1.8)  # give it more room and try again
                continue
        except Exception as e:  # never let the optional layer break the run
            last = str(e)
            code = getattr(e, "code", None)
            body_fn = getattr(e, "read", None)
            if body_fn:
                try:
                    last += " - " + json.loads(body_fn()).get("error", {}).get("message", "")
                except Exception:
                    pass
            if code in (429, 500, 502, 503, 529) and attempt < _tries - 1:
                time.sleep(5 * (attempt + 1))  # busy or rate-limited: back off and retry
                continue
            break
    with _U:
        USAGE["errors"] += 1
        USAGE["last_error"] = last
    print(f"  ! Claude call failed: {last}")
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
