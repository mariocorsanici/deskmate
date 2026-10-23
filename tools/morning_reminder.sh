#!/bin/zsh
# 9:00 reminder (mon-fri), started by the com.deskmate.morning LaunchAgent.
# If the Mac was asleep at 9 it shows up on wake, but only until noon.
# DESKMATE_DRY_RUN=1 prints the text instead of showing the alert.

root=${0:A:h:h}
(( $(date +%H) < 12 )) || [[ -n $DESKMATE_DRY_RUN ]] || exit 0

language=$(jq -r '.language // "en"' $root/data/config.json 2>/dev/null || print en)
if [[ $language == it ]]; then
  title="Buongiorno, si riparte"
  message="1. /whats-on-today: rilegge le consegne di ieri, controlla cosa è cambiato, propone l'ordine della giornata e apre le sessioni.\n2. Fai i passi «Prima di iniziare» che ti indica.\n3. Durante il giorno: /study-later <argomento> per ciò che vuoi studiare dopo."
  button="Ok, si parte"
else
  title="Good morning, let's go"
  message="1. /whats-on-today: rereads yesterday's handoff, checks what changed, suggests the order of the day and opens the sessions.\n2. Do the «Before you start» steps it lists.\n3. During the day: /study-later <topic> for anything you want to study later."
  button="Ok, let's go"
fi

if [[ -n $DESKMATE_DRY_RUN ]]; then print -r -- "$title: $message"; exit 0; fi
answer=$(osascript -e "button returned of (display alert \"$title\" message \"$message\" buttons {\"$button\"} default button 1 giving up after 3600)")
$root/tools/log_event.sh morning-reminder "${answer:-ignored}"
