#!/bin/zsh
# Appends a row to data/log.csv (token_usage.py fills in the tokens later).
# Usage: log_event.sh <event> [detail] [session] [cwd]

python3 -I - "${0:A:h:h}" "$@" <<'PY'
import csv, datetime as dt, fcntl, pathlib, sys
data = pathlib.Path(sys.argv[1]) / "data"
log = data / "log.csv"
columns = ["date", "time", "weekday", "event", "detail", "session", "cwd",
           "turns", "input_tokens", "cache_tokens", "output_tokens"]
args = (sys.argv[2:] + [""] * 4)[:4]
now = dt.datetime.now()
data.mkdir(exist_ok=True)
with (data / ".log.lock").open("w") as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    new = not log.exists()
    with log.open("a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(columns)
        w.writerow([now.strftime("%Y-%m-%d"), now.strftime("%H:%M"),
                    "mon tue wed thu fri sat sun".split()[now.weekday()], *args, "", "", "", ""])
PY
