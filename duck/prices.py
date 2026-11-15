"""Local price history (SQLite), filled one market-wide call per trading day."""
import datetime as dt
import sqlite3
import threading

_LOCK = threading.Lock()


class PriceStore:
    def __init__(self, path="data/prices.db"):
        self.db = sqlite3.connect(path, check_same_thread=False)  # read from several scans at once
        self.db.execute("CREATE TABLE IF NOT EXISTS bars (date TEXT, ticker TEXT, close REAL, high REAL,"
                        " volume REAL, PRIMARY KEY(date, ticker))")
        self.db.execute("CREATE TABLE IF NOT EXISTS days (date TEXT PRIMARY KEY, n INTEGER)")

    def have(self, date):
        return self.db.execute("SELECT 1 FROM days WHERE date=?", (date,)).fetchone() is not None

    def update(self, provider, lookback_days, end=None):
        """Fetch any missing days in the window. First run backfills (~5 min on free plan)."""
        end = end or dt.date.today() - dt.timedelta(days=1)
        d = end - dt.timedelta(days=lookback_days + 5)
        fetched = 0
        while d <= end:
            ds = d.isoformat()
            if d.weekday() < 5 and not self.have(ds):
                bars = provider.daily_bars(ds)
                self.db.executemany("INSERT OR REPLACE INTO bars VALUES (?,?,?,?,?)",
                                    [(ds, t, b["close"], b["high"], b["volume"]) for t, b in bars.items()])
                self.db.execute("INSERT OR REPLACE INTO days VALUES (?,?)", (ds, len(bars)))
                self.db.commit()
                fetched += 1
            d += dt.timedelta(days=1)
        # keep the database small
        cutoff = (end - dt.timedelta(days=max(400, lookback_days * 3))).isoformat()
        self.db.execute("DELETE FROM bars WHERE date < ?", (cutoff,))
        self.db.commit()
        return fetched

    def window(self, lookback_days):
        """Per ticker: latest close, highest close in window, avg $ volume, latest date."""
        last = self.db.execute("SELECT MAX(date) FROM days WHERE n > 0").fetchone()[0]
        if not last:
            return {}, None
        start = (dt.date.fromisoformat(last) - dt.timedelta(days=lookback_days)).isoformat()
        rows = self.db.execute(
            "SELECT ticker, MAX(close), AVG(close*volume) FROM bars WHERE date>=? AND date<=? GROUP BY ticker",
            (start, last)).fetchall()
        latest = dict(self.db.execute("SELECT ticker, close FROM bars WHERE date=?", (last,)).fetchall())
        out = {}
        for t, hi, dv in rows:
            if t in latest:
                out[t] = {"close": latest[t], "high": hi, "dollar_volume": dv or 0}
        return out, last

    def close_on_or_before(self, ticker, date):
        with _LOCK:
            r = self.db.execute("SELECT close FROM bars WHERE ticker=? AND date<=? ORDER BY date DESC LIMIT 1",
                                (ticker, date)).fetchone()
        return r[0] if r else None

    def latest(self, ticker):
        with _LOCK:
            r = self.db.execute("SELECT close FROM bars WHERE ticker=? ORDER BY date DESC LIMIT 1", (ticker,)).fetchone()
        return r[0] if r else None

    def change(self, ticker, days):
        """% change over the last `days` trading days, or None."""
        with _LOCK:
            rows = self.db.execute("SELECT close FROM bars WHERE ticker=? ORDER BY date DESC LIMIT ?",
                                   (ticker, days + 1)).fetchall()
        if len(rows) < 2 or not rows[-1][0]:
            return None
        return rows[0][0] / rows[-1][0] - 1

    def closes(self, ticker, n):
        """Last n closes, oldest first."""
        with _LOCK:
            rows = self.db.execute("SELECT close FROM bars WHERE ticker=? ORDER BY date DESC LIMIT ?",
                                   (ticker, n)).fetchall()
        return [r[0] for r in reversed(rows)]
