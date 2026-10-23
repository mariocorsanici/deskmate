#!/bin/zsh
# Avviso delle 9:00 (lun-ven), lanciato dal LaunchAgent com.bottega.buongiorno.
# Se il Mac era in stop alle 9 parte al risveglio, ma solo entro mezzogiorno.

(( $(date +%H) < 12 )) || exit 0

radice=${0:A:h:h}
messaggio="1. /che-si-fa-oggi: rilegge le consegne di ieri, controlla cosa è cambiato, propone l'ordine della giornata e apre le sessioni.\n2. Fai i passi «Prima di iniziare» che ti indica.\n3. Durante il giorno: /da-approfondire <argomento> per ciò che vuoi studiare dopo."

risposta=$(osascript -e "button returned of (display alert \"Buongiorno, si riparte\" message \"$messaggio\" buttons {\"Ok, si parte\"} default button 1 giving up after 3600)")
$radice/strumenti/registra.sh promemoria-9 "${risposta:-ignorato}"
