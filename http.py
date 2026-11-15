"""Tiny HTTP helper with per-host rate limiting and retries (stdlib only)."""
import json
import time
import urllib.error
import urllib.parse
import urllib.request

_last_call = {}


def get_json(url, params=None, headers=None, min_interval=0.0, retries=3, timeout=30):
    """GET a URL and return parsed JSON, or None on failure.

    min_interval: seconds to wait between calls to the same host (rate limiting).
    """
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    host = urllib.parse.urlparse(url).netloc
    for attempt in range(retries):
        wait = _last_call.get(host, 0) + min_interval - time.time()
        if wait > 0:
            time.sleep(wait)
        _last_call[host] = time.time()
        req = urllib.request.Request(url, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:  # rate limited: back off and retry
                time.sleep(15 * (attempt + 1))
                continue
            if e.code in (401, 403):
                print(f"  ! access denied ({e.code}) for {host} - check API key / plan")
                return None
            if e.code == 404:
                return None
            time.sleep(2 * (attempt + 1))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            time.sleep(2 * (attempt + 1))
    return None
