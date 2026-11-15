"""Did this stock fall on its own, or with its whole sector?

Compares the stock's daily moves with sector ETFs. If it moves like a sector ETF,
that sector is down too, and the stock fell no more than ~2x the sector, it's a
sector selloff rather than company news.
"""
import statistics as st

SECTORS = {
    "SMH": "Chips & AI hardware", "IBIT": "Crypto", "IGV": "Software", "XLK": "Tech",
    "XLF": "Financials", "KRE": "Regional banks", "XLE": "Energy", "XLV": "Healthcare",
    "XBI": "Biotech", "XLY": "Consumer", "XLI": "Industrials", "XLB": "Materials",
    "XLU": "Utilities", "XLP": "Consumer staples", "XLC": "Communication", "XME": "Metals & mining",
    "ITB": "Homebuilders", "XRT": "Retail",
}


def _rets(s):
    return [b / a - 1 for a, b in zip(s, s[1:]) if a and b]


class SectorCheck:
    def __init__(self, store, days=22):
        self.store, self.days = store, days
        self.etf = {}
        for t in SECTORS:
            s = store.closes(t, days)
            if len(s) >= days - 2 and all(s):
                self.etf[t] = (_rets(s), s[-1] / max(s) - 1)

    def check(self, ticker, drop, min_corr=0.6, min_sector_drop=0.05, max_ratio=2.2):
        """Return {etf, sector, sector_drop, corr, is_sector}."""
        s = self.store.closes(ticker, self.days)
        if len(s) < self.days - 2 or not all(s) or not self.etf:
            return None
        r = _rets(s)
        best = None
        for e, (er, ed) in self.etf.items():
            n = min(len(r), len(er))
            try:
                c = st.correlation(r[-n:], er[-n:])
            except st.StatisticsError:
                continue
            if best is None or c > best[0]:
                best = (c, e, ed)
        if not best:
            return None
        c, e, ed = best
        is_sector = c >= min_corr and ed <= -min_sector_drop and drop >= ed * max_ratio
        return {"etf": e, "sector": SECTORS[e], "sector_drop": ed, "corr": c, "is_sector": is_sector}
