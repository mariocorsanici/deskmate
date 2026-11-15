#!/bin/zsh
# Stop hook: updates the tokens in data/log.csv, only if the session ran deskmate skills.

root=${0:A:h:h}
data=${DESKMATE_DATA_DIR:-$root/data}
session=$(jq -r '.session_id // ""')
[[ -n $session ]] && grep -q -- "$session" "$data/log.csv" 2>/dev/null || exit 0
python3 -I $root/tools/token_usage.py --session "$session"
exit 0
