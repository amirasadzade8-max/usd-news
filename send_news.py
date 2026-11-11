"""
ارسال اخبار USD (زرد/نارنجی/قرمز) فارکس فکتوری به تلگرام
ساعت ۹:۰۰ صبح به وقت نیویورک، نیم ساعت قبل از اوپن بازار.
فقط از کتابخانه‌های استاندارد پایتون استفاده می‌کند.
"""

import html
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
FEED_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
CURRENCY = "USD"
IMPACTS = {"High", "Medium", "Low"}   # قرمز، نارنجی، زرد  (برای حذف زرد: "Low" را بردار)
SEND_HOUR_NY = 9                      # ساعت ارسال به وقت نیویورک

EMOJI = {"High": "🔴", "Medium": "🟠", "Low": "🟡"}

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
FORCE = os.environ.get("FORCE") == "1"


def fetch_feed():
    last_err = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(FEED_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        except Exception as e:
            last_err = e
            print(f"fetch attempt {attempt + 1} failed: {e}", file=sys.stderr)
            time.sleep(15 * (attempt + 1))
    sys.exit(f"Could not fetch feed: {last_err}")


def send(text: str):
    data = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": "true",
    }).encode()
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    with urllib.request.urlopen(url, data=data, timeout=20) as r:
        print("Telegram:", r.status)


def main():
    now = datetime.now(NY)

    # دو cron (برای ساعت تابستانی و زمستانی) داریم؛ فقط اجرایی که
    # در نیویورک ساعتش ۹ است پیام می‌فرستد.
    if not FORCE and (now.hour != SEND_HOUR_NY or now.weekday() >= 5):
        print(f"Skip: NY time is {now:%a %H:%M}")
        return

    events = []
    for e in fetch_feed():
        if e.get("country") != CURRENCY or e.get("impact") not in IMPACTS:
            continue
        try:
            dt = datetime.fromisoformat(e["date"]).astimezone(NY)
        except Exception:
            continue
        if dt.date() == now.date():
            events.append((dt, e))
    events.sort(key=lambda x: x[0])

    header = f"📰 <b>اخبار USD امروز</b> – {now:%A %Y-%m-%d}\n🕘 اوپن ۹:۳۰ | همه ساعت‌ها به وقت نیویورک (ET)\n"

    if not events:
        send(header + "\n✅ امروز خبر زرد/نارنجی/قرمزی برای USD نیست.")
        return

    lines = [header]
    for dt, e in events:
        extra = []
        if e.get("forecast"):
            extra.append(f"پیش‌بینی: {html.escape(e['forecast'])}")
        if e.get("previous"):
            extra.append(f"قبلی: {html.escape(e['previous'])}")
        line = f"{EMOJI[e['impact']]} <code>{dt:%H:%M}</code> – {html.escape(e['title'])}"
        if extra:
            line += "\n      " + " | ".join(extra)
        lines.append(line)

    send("\n".join(lines)[:4000])


if __name__ == "__main__":
    main()
