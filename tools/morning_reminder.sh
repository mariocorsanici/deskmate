#!/bin/zsh
# Morning reminder, started at login and at the time set in data/config.json.
# DESKMATE_DRY_RUN=1 prints the text instead of showing the alert.

root=${0:A:h:h}
exec python3 -I "$root/bin/deskmate" reminders display morning
