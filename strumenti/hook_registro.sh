#!/bin/zsh
# Hook UserPromptSubmit: registra in registro.csv ogni lancio delle skill della bottega.

radice=${0:A:h:h}
input=$(cat)
prompt=$(jq -r '.prompt // ""' <<< "$input")
[[ $prompt =~ '^[[:space:]]*/(che-si-fa-oggi|com-e-andata|chiudi-bottega|da-approfondire)([[:space:]]+(.*))?$' ]] || exit 0
$radice/strumenti/registra.sh "${match[1]}" "${match[3]}" \
  "$(jq -r '.session_id // ""' <<< "$input")" "$(jq -r '.cwd // ""' <<< "$input")"
exit 0
