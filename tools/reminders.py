#!/usr/bin/env python3
"""Reminders driven by data/config.json: texts, time windows, LaunchAgents, calendar file.

Usage:
  reminders.py check                     validates the reminders section of config.json
  reminders.py text <morning|evening>    title on the first line, then the alert message
  reminders.py window <morning|evening>  exit 0 if now is a good time to show the alert
  reminders.py plist <morning|evening>   LaunchAgent for the mac channel, on stdout
  reminders.py ics                       writes data/deskmate-reminders.ics, prints "changed" or "unchanged"
"""
import datetime as dt
import json
import pathlib
import plistlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ICS = DATA / "deskmate-reminders.ics"
DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
RETRO_DAYS = {"mon", "wed", "fri"}
CHANNELS = {"mac", "calendar", "slack"}
DEFAULTS = {"morning": "09:00", "evening": "17:00",
            "days": ["mon", "tue", "wed", "thu", "fri"], "channels": ["mac"]}

TEXTS = {
    "en": {
        "morning_title": "Good morning, let's go",
        "morning": ["/whats-on-today: rereads yesterday's handoff, checks what changed, suggests the order of the day and opens the sessions.",
                    "Do the «Before you start» steps it lists.",
                    "During the day: /study-later <topic> for anything you want to study later."],
        "evening_title": "Time to call it a day",
        "checkpoint": "/checkpoint in each work session: saves where the project stands in its project card.",
        "retro": "/how-did-it-go: retrospective on how the last few days went, updates the lessons.",
        "retro_days": "(Mon, Wed, Fri) ",
        "close": "/call-it-a-day: snapshots the open sessions, writes tomorrow's handoff and suggests topics to study.",
        "after": "After closing: study ({n} topics to study) or admin work.",
        "after_static": "After closing: study the topics you set aside, or admin work.",
        "morning_button": "Ok, let's go", "snooze": "In 30 minutes", "done": "Ok, closing",
    },
    "it": {
        "morning_title": "Buongiorno, si riparte",
        "morning": ["/whats-on-today: rilegge le consegne di ieri, controlla cosa è cambiato, propone l'ordine della giornata e apre le sessioni.",
                    "Fai i passi «Prima di iniziare» che ti indica.",
                    "Durante il giorno: /study-later <argomento> per ciò che vuoi studiare dopo."],
        "evening_title": "È ora di chiudere",
        "checkpoint": "/checkpoint in ogni sessione di lavoro: salva lo stato del progetto nella sua scheda.",
        "retro": "/how-did-it-go: retrospettiva sul metodo degli ultimi giorni, aggiorna le lezioni.",
        "retro_days": "(lun, mer, ven) ",
        "close": "/call-it-a-day: fotografa le sessioni aperte, scrive le consegne per domani e propone argomenti da approfondire.",
        "after": "Dopo la chiusura: studio ({n} argomenti da approfondire) o amministrazione.",
        "after_static": "Dopo la chiusura: studio degli argomenti messi da parte, o amministrazione.",
        "morning_button": "Ok, si parte", "snooze": "Tra 30 minuti", "done": "Ok, chiudo",
    },
}


def config():
    try:
        c = json.loads((DATA / "config.json").read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        c = {}
    return c, {**DEFAULTS, **c.get("reminders", {})}


def texts(c):
    return TEXTS.get(c.get("language"), TEXTS["en"])


def hour_minute(value):
    h, m = map(int, value.split(":"))
    return h, m


def lines(kind, t, static=False):
    if kind == "morning":
        return t["morning"]
    open_topics = 0
    try:
        open_topics = sum(l.startswith("- [ ]") for l in (DATA / "study-later.md").read_text().splitlines())
    except FileNotFoundError:
        pass
    after = t["after_static"] if static else t["after"].format(n=open_topics)
    if static:
        return [t["checkpoint"], t["retro_days"] + t["retro"], t["close"], after]
    today = DAYS[dt.date.today().weekday()]
    return [t["checkpoint"]] + ([t["retro"]] if today in RETRO_DAYS else []) + [t["close"], after]


def numbered(items, sep):
    return sep.join(f"{i}. {x}" for i, x in enumerate(items, 1))


def fold(line):
    """Splits a calendar line into 75-byte chunks, as the iCalendar format requires."""
    raw, out = line.encode(), []
    while len(raw) > 75:
        cut = 75 if not out else 74
        while raw[cut] & 0xC0 == 0x80:  # don't split a UTF-8 character
            cut -= 1
        out.append(raw[:cut].decode())
        raw = raw[cut:]
    out.append(raw.decode())
    return "\r\n ".join(out)


def check(r):
    errors = []
    for kind in ("morning", "evening"):
        if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", str(r[kind])):
            errors.append(f"{kind}: '{r[kind]}' is not a HH:MM time")
    if not r["days"] or set(r["days"]) - set(DAYS):
        errors.append(f"days: use a non-empty list of {', '.join(DAYS)}")
    if set(r["channels"]) - CHANNELS:
        errors.append(f"channels: use any of {', '.join(sorted(CHANNELS))}")
    return errors


def main():
    cmd, kind = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else None)
    c, r = config()
    t = texts(c)

    if cmd == "check":
        errors = check(r)
        print("\n".join(errors) or "ok")
        sys.exit(1 if errors else 0)

    if cmd == "text":
        # literal \n between items: AppleScript turns it into a line break
        print(t[f"{kind}_title"])
        print(numbered(lines(kind, t), "\\n"))
        if kind == "morning":
            print(t["morning_button"])
        else:
            print(t["snooze"])
            print(t["done"])

    elif cmd == "window":
        # if the Mac was asleep at reminder time, launchd fires on wake: show it only while it still makes sense
        h, m = hour_minute(r[kind])
        now = dt.datetime.now()
        start = now.replace(hour=h, minute=m, second=0, microsecond=0)
        before, after = (dt.timedelta(minutes=5), dt.timedelta(hours=3)) if kind == "morning" \
            else (dt.timedelta(hours=1), dt.timedelta(hours=4))
        sys.exit(0 if start - before <= now <= start + after else 1)

    elif cmd == "plist":
        h, m = hour_minute(r[kind])
        weekdays = [DAYS.index(d) + 1 for d in r["days"]]  # launchd: 1 = Monday ... 7 = Sunday
        sys.stdout.write(plistlib.dumps({
            "Label": f"com.deskmate.{kind}",
            "ProgramArguments": [str(ROOT / "tools" / f"{kind}_reminder.sh")],
            "StartCalendarInterval": [{"Weekday": d % 7, "Hour": h, "Minute": m} for d in weekdays],
        }).decode())

    elif cmd == "ics":
        byday = ",".join(d[:2].upper() for d in r["days"])
        # first occurrence on one of the chosen days, otherwise some calendars show an extra event on DTSTART
        first = dt.date.today()
        while DAYS[first.weekday()] not in r["days"]:
            first += dt.timedelta(days=1)
        start = first.strftime("%Y%m%d")
        events = []
        for k in ("morning", "evening"):
            h, m = hour_minute(r[k])
            body = numbered(lines(k, t, static=True), "\\n").replace(",", "\\,").replace(";", "\\;")
            events += ["BEGIN:VEVENT", f"UID:deskmate-{k}@deskmate", f"DTSTAMP:{start}T000000Z",
                       f"DTSTART:{start}T{h:02d}{m:02d}00", "DURATION:PT15M",
                       f"RRULE:FREQ=WEEKLY;BYDAY={byday}", f"SUMMARY:deskmate · {t[k + '_title']}",
                       f"DESCRIPTION:{body}", "TRANSP:TRANSPARENT",
                       "BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{t[k + '_title']}", "TRIGGER:PT0M", "END:VALARM",
                       "END:VEVENT"]
        content = "\r\n".join(fold(l) for l in ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//deskmate//reminders//EN",
                               "CALSCALE:GREGORIAN", *events, "END:VCALENDAR"]) + "\r\n"
        # the dates in DTSTAMP and DTSTART change daily: compare without them, keeping the start time
        strip = lambda s: re.sub(r"DTSTAMP:\S+|DTSTART:\d{8}", "", s)
        old = ICS.read_bytes().decode() if ICS.exists() else ""  # bytes: keep the \r\n line endings
        if strip(old) == strip(content):
            print("unchanged")
        else:
            ICS.write_bytes(content.encode())
            print("changed")


if __name__ == "__main__":
    main()
