"""Extract weekly S&P 500 price events from the archived Yahoo daily chart response."""
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo


def extract(chart):
    quotes = chart["chart"]["result"][0]
    weeks = {}
    for timestamp, close in zip(quotes["timestamp"], quotes["indicators"]["quote"][0]["close"], strict=True):
        day = datetime.fromtimestamp(timestamp, ZoneInfo("America/New_York")).date()
        if close is not None and day <= date(2026, 11, 20):
            weeks[day - timedelta(days=day.weekday())] = {"day": day.isoformat(), "close": round(close, 2)}
    events = []
    week = timedelta(weeks=1)
    for monday, current in sorted(weeks.items()):
        previous = weeks.get(monday - week)
        if monday.year < 1990 or previous is None:
            continue
        if current["close"] / previous["close"] <= 0.92:
            events.append({"previous": previous, "event": current, "next_week": weeks.get(monday + week),
                           "four_weeks_later": weeks.get(monday + 4 * week)})
    return events


if __name__ == "__main__":
    print(json.dumps(extract(json.loads(Path(sys.argv[1]).read_bytes())), indent=2))
