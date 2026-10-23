#!/bin/zsh
# 17:00 reminder (mon-fri), started by the com.deskmate.evening LaunchAgent.
# The snooze button shows it again 30 minutes later. If the Mac was asleep at 17
# it shows up on wake, but only until 21.
# DESKMATE_DRY_RUN=1 prints the text instead of showing the alert.

root=${0:A:h:h}
(( $(date +%H) >= 16 && $(date +%H) < 21 )) || [[ -n $DESKMATE_DRY_RUN ]] || exit 0

language=$(jq -r '.language // "en"' $root/data/config.json 2>/dev/null || print en)
open=$(grep -c '^- \[ \]' $root/data/study-later.md 2>/dev/null)
retro_day=false
case $(date +%u) in 1|3|5) retro_day=true ;; esac

if [[ $language == it ]]; then
  title="È ora di chiudere"
  retro="/how-did-it-go: retrospettiva sul metodo degli ultimi giorni, aggiorna le lezioni."
  close="/call-it-a-day: fotografa le sessioni aperte, scrive le consegne per domani e propone argomenti da approfondire."
  after="Dopo la chiusura: studio ($open argomenti da approfondire) o amministrazione."
  snooze="Tra 30 minuti"; done_button="Ok, chiudo"
else
  title="Time to call it a day"
  retro="/how-did-it-go: retrospective on how the last few days went, updates the lessons."
  close="/call-it-a-day: snapshots the open sessions, writes tomorrow's handoff and suggests topics to study."
  after="After closing: study ($open topics to study) or admin work."
  snooze="In 30 minutes"; done_button="Ok, closing"
fi
if $retro_day; then message="1. $retro\n2. $close\n3. $after"; else message="1. $close\n2. $after"; fi

if [[ -n $DESKMATE_DRY_RUN ]]; then print -r -- "$title: $message"; exit 0; fi
while true; do
  answer=$(osascript -e "button returned of (display alert \"$title\" message \"$message\" buttons {\"$snooze\", \"$done_button\"} default button 2 giving up after 3600)")
  $root/tools/log_event.sh evening-reminder "${answer:-ignored}"
  [[ $answer == $snooze ]] || break
  sleep 1800
done
