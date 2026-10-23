#!/bin/zsh
# Avviso delle 17:00 (lun-ven), lanciato dal LaunchAgent com.bottega.promemoria.
# "Tra 30 minuti" lo ripropone più tardi. Se il Mac era in stop alle 17 parte al risveglio, ma solo fino alle 21.

(( $(date +%H) >= 16 && $(date +%H) < 21 )) || exit 0

radice=${0:A:h:h}
aperte=$(grep -c '^- \[ \]' $radice/dati/da-approfondire.md 2>/dev/null)
passi="/chiudi-bottega: fotografa le sessioni aperte, scrive le consegne per domani e propone argomenti da approfondire.\n2. Dopo bottega: studio ($aperte argomenti da approfondire) o amministrazione."
case $(date +%u) in
  1|3|5) messaggio="1. /com-e-andata: retrospettiva sul metodo degli ultimi giorni, aggiorna le lezioni.\n2. ${passi/2. /3. }" ;;
  *)     messaggio="1. $passi" ;;
esac

while true; do
  risposta=$(osascript -e "button returned of (display alert \"È ora di chiudere bottega\" message \"$messaggio\" buttons {\"Tra 30 minuti\", \"Ok, chiudo\"} default button 2 giving up after 3600)")
  $radice/strumenti/registra.sh promemoria-17 "${risposta:-ignorato}"
  [[ $risposta == "Tra 30 minuti" ]] || break
  sleep 1800
done
