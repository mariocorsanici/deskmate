#!/bin/zsh
# Evening reminder, started by the com.deskmate.evening LaunchAgent at the time set in data/config.json.
# The snooze button shows it again 30 minutes later.
# DESKMATE_DRY_RUN=1 prints the text instead of showing the alert.

root=${0:A:h:h}
[[ -n $DESKMATE_DRY_RUN ]] || python3 -I "$root/bin/deskmate" reminders window evening || exit 0

while true; do
  lines=("${(@f)$(python3 -I "$root/bin/deskmate" reminders text evening --with-provider)}") || exit $?
  title=$lines[1] message=$lines[2] snooze=$lines[3] done_button=$lines[4] provider=$lines[5]
  if [[ -n $DESKMATE_DRY_RUN ]]; then print -r -- "$title: $message"; exit 0; fi
  answer=$(osascript -e "button returned of (display alert \"$title\" message \"$message\" buttons {\"$snooze\", \"$done_button\"} default button 2 giving up after 3600)")
  python3 -I "$root/bin/deskmate" reminders respond evening "${answer:-ignored}" --provider "$provider" || exit $?
  [[ $answer == $snooze ]] || break
  sleep 1800
done
