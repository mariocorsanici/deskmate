#!/bin/zsh
# Logs every run of the deskmate skills in data/log.csv. Two hooks, two ways a skill starts:
# - UserPromptSubmit: the user types the command at the start of the message ("/call-it-a-day");
# - PreToolUse on the Skill tool: Claude starts it, e.g. when the command is inside a sentence
#   ("let's close the day /call-it-a-day"). A command merely mentioned in a sentence is not logged.

root=${0:A:h:h}
skills='^(whats-on-today|how-did-it-go|call-it-a-day|study-later|checkpoint)$'
input=$(cat)
if [[ $(jq -r '.hook_event_name // ""' <<< "$input") == PreToolUse ]]; then
  name=$(jq -r '.tool_input.skill // ""' <<< "$input")
  args=$(jq -r '.tool_input.args // ""' <<< "$input")
else
  prompt=$(jq -r '.prompt // ""' <<< "$input")
  [[ $prompt =~ '^[[:space:]]*/([a-z-]+)([[:space:]]+(.*))?$' ]] || exit 0
  name=${match[1]} args=${match[3]}
fi
[[ $name =~ $skills ]] || exit 0
$root/tools/log_event.sh "$name" "$args" \
  "$(jq -r '.session_id // ""' <<< "$input")" "$(jq -r '.cwd // ""' <<< "$input")"
exit 0
