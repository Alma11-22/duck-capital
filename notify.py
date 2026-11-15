"""Optional morning email with the top picks and early warnings.

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


def send(date, drops, warnings, paper_stats):
    to, user, pw = os.environ.get("EMAIL_TO"), os.environ.get("SMTP_USER"), os.environ.get("SMTP_PASSWORD")
    if not (to and user and pw):
        print("    (email not set up - skipping)")
        return False
    e = html.escape
    url = os.environ.get("REPORT_URL", "")
    rows = "".join(
        f"<tr><td><b>{e(d['ticker'])}</b></td><td>{d['score']}</td><td>{d['drop']:+.0%}</td>"
        f"<td>{e(BUCKET_LABEL[d['bucket']])}</td></tr>" for d in drops[:8]) or "<tr><td colspan=4>None today</td></tr>"
    warns = "".join(f"<li><b>{e(w['ticker'])}</b>: {e((w['headlines'] + w['red_flags'] + [''])[0])}</li>"
                    for w in warnings[:5]) or "<li>None today</li>"
    hit = f"{paper_stats['hit_rate']:.0%}" if paper_stats["hit_rate"] is not None else "–"
    body = (f"<div style='font-family:sans-serif;font-size:14px'>"
            f"<h3 style='margin:0'>Rebound AI – {e(date)}</h3>"
            f"<p>{len(drops)} rebound candidates · {len(warnings)} early warnings · "
            f"paper hit rate {hit} on {paper_stats['n']} picks</p>"
            f"<b>Early warnings</b><ul>{warns}</ul>"
            f"<b>Top rebound candidates</b><table cellpadding=4 style='border-collapse:collapse'>"
            f"<tr><th align=left>Stock</th><th>Score</th><th>Drop</th><th align=left>Kind</th></tr>{rows}</table>"
            + (f"<p><a href='{e(url)}'>Open the full report</a></p>" if url else "")
            + "<p style='color:#888;font-size:12px'>Not investment advice.</p></div>")
    msg = MIMEText(body, "html")
    msg["Subject"] = f"Rebound AI {date}: {len(drops)} candidates, {len(warnings)} warnings"
    msg["From"], msg["To"] = user, to
    try:
        host, port = os.environ.get("SMTP_HOST", "smtp.gmail.com"), int(os.environ.get("SMTP_PORT", "465"))
        with smtplib.SMTP_SSL(host, port, timeout=30) as s:
            s.login(user, pw)
            s.sendmail(user, [x.strip() for x in to.split(",")], msg.as_string())
        print(f"    emailed {to}")
        return True
    except Exception as ex:  # email must never break the scan
        print(f"    ! email failed: {ex}")
        return False
