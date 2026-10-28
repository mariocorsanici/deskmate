#!/bin/zsh
# UserPromptSubmit hook: logs every run of the deskmate skills in data/log.csv.

root=${0:A:h:h}
input=$(cat)
prompt=$(jq -r '.prompt // ""' <<< "$input")
[[ $prompt =~ '^[[:space:]]*/(whats-on-today|how-did-it-go|call-it-a-day|study-later|checkpoint)([[:space:]]+(.*))?$' ]] || exit 0
$root/tools/log_event.sh "${match[1]}" "${match[3]}" \
  "$(jq -r '.session_id // ""' <<< "$input")" "$(jq -r '.cwd // ""' <<< "$input")"
exit 0
