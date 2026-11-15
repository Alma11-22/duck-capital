"""Optional morning email with live events, top picks and early warnings.

Sends only if these are set (e.g. as GitHub secrets):
  EMAIL_TO            where to send it (comma-separate several people)
  SMTP_USER           the sending Gmail address
  SMTP_PASSWORD       a Gmail *app password* (not your normal password)
  SMTP_HOST / SMTP_PORT   optional; default Gmail (smtp.gmail.com:465)
  REPORT_URL          optional link to the full web page
"""
import html
import os
import smtplib
from email.mime.text import MIMEText

from .score import BUCKET_LABEL


def send(date, live, drops, warnings, stats):
    to, user, pw = os.environ.get("EMAIL_TO"), os.environ.get("SMTP_USER"), os.environ.get("SMTP_PASSWORD")
    if not (to and user and pw):
        print("    (email not set up - skipping)")
        return False
    e = html.escape
    url = os.environ.get("REPORT_URL", "")
    evs = "".join(
        f"<li><b>{e(ev['label'])}</b>{' (market confirms)' if ev['confirmed'] else ''}: top winners "
        f"{e(', '.join(w['ticker'] for w in ev.get('winners', [])[:4]))}</li>" for ev in live) or "<li>None today</li>"
    rows = "".join(
        f"<tr><td><b>{e(d['ticker'])}</b></td><td>{d['score']}</td><td>{d['drop']:+.0%}</td>"
        f"<td>{e(BUCKET_LABEL[d['bucket']])}</td><td>{e(d.get('psych_label', ''))}</td></tr>" for d in drops[:8]) \
        or "<tr><td colspan=5>None today</td></tr>"
    warns = "".join(f"<li><b>{e(w['ticker'])}</b>: {e((w['why'] + [''])[0])}</li>"
                    for w in warnings[:5]) or "<li>None today</li>"
    s = stats["all"]
    hit = f"{s['hit_rate']:.0%}" if s["hit_rate"] is not None else "–"
    body = (f"<div style='font-family:Archivo,Helvetica,Arial,sans-serif;font-size:14px;color:#0B100F'>"
            f"<div style='font:600 12px Georgia,serif;letter-spacing:.3em'>DUCK CAPITAL</div>"
            f"<h2 style='font:400 24px Georgia,serif;margin:6px 0'>{e(date)}</h2>"
            f"<p>{len(live)} live events · {len(drops)} rebounds to watch · {len(warnings)} before the move · "
            f"paper hit rate {hit} on {s['n']} picks</p>"
            f"<b>Live events</b><ul>{evs}</ul>"
            f"<b>Before the move</b><ul>{warns}</ul>"
            f"<b>Top rebound candidates</b><table cellpadding=4 style='border-collapse:collapse'>"
            f"<tr><th align=left>Stock</th><th>Score</th><th>Drop</th><th align=left>Kind</th>"
            f"<th align=left>Numbers</th></tr>{rows}</table>"
            + (f"<p><a href='{e(url)}' style='display:inline-block;background:#21ABC9;color:#0B100F;"
               f"padding:10px 18px;border-radius:999px;text-decoration:none;font-weight:600'>Open the full report</a></p>"
               if url else "")
            + "<p style='color:#888;font-size:12px'>Not investment advice.</p></div>")
    msg = MIMEText(body, "html")
    msg["Subject"] = f"Duck Capital {date}: {len(live)} events, {len(drops)} rebounds, {len(warnings)} before the move"
    msg["From"], msg["To"] = user, to
    try:
        host, port = os.environ.get("SMTP_HOST", "smtp.gmail.com"), int(os.environ.get("SMTP_PORT", "465"))
        with smtplib.SMTP_SSL(host, port, timeout=30) as srv:
            srv.login(user, pw)
            srv.sendmail(user, [x.strip() for x in to.split(",")], msg.as_string())
        print(f"    emailed {to}")
        return True
    except Exception as ex:  # email must never break the scan
        print(f"    ! email failed: {ex}")
        return False
