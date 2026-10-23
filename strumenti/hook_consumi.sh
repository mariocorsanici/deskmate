#!/bin/zsh
# Hook Stop: aggiorna i token in registro.csv, solo se la sessione ha lanciato skill della bottega.

radice=${0:A:h:h}
sessione=$(jq -r '.session_id // ""')
[[ -n $sessione ]] && grep -q -- "$sessione" $radice/dati/registro.csv 2>/dev/null || exit 0
python3 -I $radice/strumenti/consumi.py --sessione "$sessione"
exit 0
