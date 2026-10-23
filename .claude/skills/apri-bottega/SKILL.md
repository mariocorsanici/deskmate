---
name: apri-bottega
description: Installa o ricontrolla la bottega su questo Mac (skill, hook, promemoria) e verifica che tutto risponda.
disable-model-invocation: true
---

# Apri bottega

Prepara il Mac per le skill della bottega, oppure fa un controllo di salute se è già installata. Scrivi in italiano semplice; Mario non deve conoscere launchd o gli hook per capire l'esito.

## Passi

1. **Posizione.** La repo deve stare in `~/Dev/bottega`: le skill cercano lì dati e script. Se la cartella corrente è altrove, proponi di spostarla e fermati finché non è a posto.

2. **Installa.** Esegui `./installa.sh` dalla radice della repo e leggi l'output. Ogni `✗` blocca: spiega cosa manca e come installarlo (per esempio `brew install jq`), poi rilancia. Ogni `!` è un avviso: riportalo con una frase su cosa comporta.

3. **Verifica.** Controlla che ogni pezzo risponda davvero, non solo che esista:
   - le 4 skill della giornata sono collegamenti a `skills/` di questa repo: `ls -l ~/.claude/skills`;
   - gli hook sono in `~/.claude/settings.json`: `jq .hooks ~/.claude/settings.json`;
   - gli script degli hook funzionano: passa a `strumenti/hook_registro.sh` un JSON di prova (`{"prompt":"/da-approfondire prova","session_id":"verifica","cwd":"/"}`), controlla che la riga compaia in `dati/registro.csv` e poi toglila;
   - i promemoria sono caricati: `launchctl print gui/$(id -u)/com.bottega.buongiorno` e `.../com.bottega.promemoria`.
   Fatto quando ogni punto ha un esito osservato.

4. **Riepilogo.** In chat, una riga per pezzo con ✓ o il problema rimasto. Ricorda che le sessioni di Claude già aperte vedono gli hook solo dopo un riavvio, e che il giorno tipo è: `/che-si-fa-oggi` al mattino, `/da-approfondire` durante il giorno, `/com-e-andata` (lun, mer, ven) e `/chiudi-bottega` verso le 17.

Per togliere tutto: `./installa.sh --rimuovi` (i dati restano).
