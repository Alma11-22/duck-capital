"""Optional Claude judgment layer: temporary scare or real damage?

Only runs if ANTHROPIC_API_KEY is set. Reviews the top-scored names and can
move the score by up to +/-15 points, with a one-paragraph thesis.
"""
import json
import os
import urllib.request

PROMPT = """You are a skeptical equity analyst. A stock sold off on bad news.
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


def review(stock, news, result, cfg):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key or not cfg.get("use_claude"):
        return None
    heads = "\n".join(f"- {n['headline']}" for n in news[:12]) or "- (no headlines found)"
    body = {
        "model": cfg["claude_model"], "max_tokens": 400,
        "messages": [{"role": "user", "content": PROMPT.format(
            name=stock["name"], ticker=stock["ticker"], industry=stock["industry"],
            drop=-stock["drop"], lookback=cfg["lookback_days"], bucket=stock["bucket"],
            headlines=heads, checks="; ".join(result["reasons"]), analogs=", ".join(result["analogs"]))}],
    }
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode(),
                                 headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                                          "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            text = json.loads(r.read())["content"][0]["text"]
        text = text[text.find("{"): text.rfind("}") + 1]
        out = json.loads(text)
        out["adjust"] = max(-15, min(15, int(out.get("adjust", 0))))
        return out
    except Exception as e:  # never let the optional layer break the run
        print(f"  ! Claude review failed for {stock['ticker']}: {e}")
        return None
