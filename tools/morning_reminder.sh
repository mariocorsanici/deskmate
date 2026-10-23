#!/bin/zsh
# Morning reminder, started by the com.deskmate.morning LaunchAgent at the time set in data/config.json.
# DESKMATE_DRY_RUN=1 prints the text instead of showing the alert.

root=${0:A:h:h}
[[ -n $DESKMATE_DRY_RUN ]] || python3 -I $root/tools/reminders.py window morning || exit 0

lines=("${(@f)$(python3 -I $root/tools/reminders.py text morning)}")
title=$lines[1] message=$lines[2] button=$lines[3]

if [[ -n $DESKMATE_DRY_RUN ]]; then print -r -- "$title: $message"; exit 0; fi
answer=$(osascript -e "button returned of (display alert \"$title\" message \"$message\" buttons {\"$button\"} default button 1 giving up after 3600)")
$root/tools/log_event.sh morning-reminder "${answer:-ignored}"
