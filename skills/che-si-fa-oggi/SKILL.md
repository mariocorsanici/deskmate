---
name: che-si-fa-oggi
description: Inizio giornata - rilegge le consegne, controlla cosa è cambiato e riapre le sessioni.
disable-model-invocation: true
---

# Che si fa oggi

Rimetti Mario in pista in pochi minuti partendo dalle consegne scritte da `/chiudi-bottega`. I file di dati sono in `~/Dev/bottega/dati/`. Scrivi in italiano semplice, frasi brevi.

## Passi

1. **Leggi.** `~/Dev/bottega/dati/consegne.md` e, in `~/Dev/bottega/dati/lezioni.md`, gli esperimenti dell'ultima voce. Se le consegne non sono di ieri (o di venerdì, di lunedì), dillo e chiedi se ricostruirle con `python3 -I ~/Dev/bottega/strumenti/sessioni.py --da <data>`.

2. **Passaggi mancati.** In `~/Dev/bottega/dati/registro.csv` controlla l'ultimo giorno lavorativo: c'è `chiudi-bottega`? Se era lunedì, mercoledì o venerdì, c'è `com-e-andata`? I promemoria (`promemoria-9`, `promemoria-17`) dicono se l'avviso è arrivato e cosa hai risposto. Segnala in una riga solo ciò che manca.

3. **Aggiorna.** Le consegne sono una fotografia di ieri sera. Per ogni punto che dipende da altri o da uno stato esterno (approvazioni, PR, CI, risposte attese), controlla lo stato attuale con un comando. Fatto quando ogni "Aspetti" ha uno stato di stamattina.

4. **Proponi la giornata.** In chat, breve:
   - **Prima di iniziare:** i passi di preparazione dalle consegne.
   - **Ordine consigliato:** prima ciò che sblocca altri (messaggi da mandare, risposte da dare), poi il lavoro lungo.
   - **Metodo:** gli esperimenti in corso da `lezioni.md`, una riga ciascuno, così li tieni a mente.
   - Il numero di voci aperte in `da-approfondire.md`, senza elencarle: sono per dopo le 17.

5. **Apri le sessioni.** Chiedi quali aprire e aprile in tab separate di iTerm:

   ```bash
   osascript <<'EOF'
   tell application "iTerm"
     activate
     if (count of windows) = 0 then create window with default profile
     tell current window
       set t to (create tab with default profile)
       tell current session of t to write text "cd <cartella> && claude --resume <id>"
     end tell
   end tell
   EOF
   ```

   Ripeti il blocco `create tab` per ogni sessione. Se un ID non si apre, suggerisci `claude --resume` dalla cartella della sessione per sceglierla dall'elenco.
