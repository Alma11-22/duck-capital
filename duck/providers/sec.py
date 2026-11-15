"""SEC EDGAR - free, no key. Needs a contact email in the User-Agent.

Gives recent 8-K filings with item codes, which are some of the earliest
red flags a company is legally forced to publish, plus Form 4 (insider) counts.
"""
import datetime as dt
import os

from ..http import get_json

# 8-K items that tend to come before (or with) a selloff
RED_FLAG_ITEMS = {
    "1.05": "Cybersecurity incident",
    "2.06": "Material impairment / writedown",
    "3.01": "Delisting notice",
    "4.01": "Auditor change",
    "4.02": "Past financials can't be relied on",
    "5.02": "Executive / director departure",
    "2.05": "Restructuring / layoffs",
}


class SEC:
    def __init__(self, email=None):
        email = email or os.environ.get("SEC_CONTACT_EMAIL", "duck-capital@example.com")
        self.headers = {"User-Agent": f"DuckCapital research {email}"}
        self._cik = None

    def _cik_map(self):
        if self._cik is None:
            d = get_json("https://www.sec.gov/files/company_tickers.json",
                         headers=self.headers, min_interval=0.15) or {}
            self._cik = {v["ticker"].upper(): str(v["cik_str"]).zfill(10) for v in d.values()}
        return self._cik

    def filings(self, ticker, days=30):
        """Returns {"red_flags": [...], "form4_count": n} for the last `days`."""
        cik = self._cik_map().get(ticker.upper().replace(".", "-"))
        if not cik:
            return {"red_flags": [], "form4_count": 0}
        d = get_json(f"https://data.sec.gov/submissions/CIK{cik}.json",
                     headers=self.headers, min_interval=0.15)
        if not d:
            return {"red_flags": [], "form4_count": 0}
        recent = d.get("filings", {}).get("recent", {})
        cutoff = (dt.date.today() - dt.timedelta(days=days)).isoformat()
        flags, form4 = [], 0
        for form, date, items in zip(recent.get("form", []), recent.get("filingDate", []),
                                     recent.get("items", [""] * len(recent.get("form", [])))):
            if date < cutoff:
                continue
            if form == "4":
                form4 += 1
            if form == "8-K":
                for code in (items or "").split(","):
                    code = code.strip()
                    if code in RED_FLAG_ITEMS:
                        flags.append(f"{date}: {RED_FLAG_ITEMS[code]} (8-K {code})")
        return {"red_flags": flags, "form4_count": form4}
