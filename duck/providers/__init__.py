"""Data providers. Each one exposes the same small interface so a paid
provider can be swapped in later without touching the scanners.

Prices (whole market):   daily_bars(date) -> {ticker: {"close","volume","high"}}
Per-company details:     profile, news, metrics, insiders, recommendations, filings
"""
