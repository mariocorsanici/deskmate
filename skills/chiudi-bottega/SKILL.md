---
name: chiudi-bottega
description: Fine giornata - fotografa le sessioni Claude aperte e scrive le consegne per domani.
disable-model-invocation: true
---

# Chiudi bottega

Lasci a Mario di domani le **consegne**: per ogni lavoro aperto, dove è arrivato, cosa resta da fare e come riprenderlo. I file di dati sono in `~/Dev/bottega/dati/`. Scrivi in italiano semplice, frasi brevi, niente gergo non spiegato.

## Passi

1. **Retrospettiva.** Se oggi è lunedì, mercoledì o venerdì e `~/Dev/bottega/dati/lezioni.md` non ha ancora una voce di oggi, chiedi se fare prima `/com-e-andata`. Se dice di sì, fermati qui: la rilancerà dopo.

2. **Raccogli.** Esegui `python3 -I ~/Dev/bottega/strumenti/sessioni.py` (le sessioni di oggi). Rileggi anche `~/Dev/bottega/dati/consegne.md`: le sessioni con lavoro aperto che oggi non sono state toccate restano nelle consegne, segnate "non toccata oggi".
   - Salta questa sessione e quelle che hanno solo lanciato le skill della bottega.
   - Se gli ultimi messaggi non bastano a capire lo stato, rilancia con `--messaggi 40` o leggi il transcript.
   Fatto quando ogni sessione è classificata come **aperta** (resta qualcosa da fare o da aspettare) o **chiusa** (finita, va solo nel riepilogo).

3. **Verifica lo stato vivo.** Le consegne sono una fotografia: dove un punto dipende da uno stato controllabile con un comando (PR, CI, branch, servizio remoto), controllalo adesso e scrivi l'esito con l'ora. Fatto quando nessuna consegna riporta uno stato preso solo dalla memoria del transcript che si poteva verificare.

4. **Scrivi.** Sposta il vecchio `consegne.md` in `archivio/AAAA-MM-GG.md` (la data del suo titolo), poi scrivi il nuovo con questa forma:

   ```markdown
   # Consegne per <giorno> <data>

   ## In breve
   - una riga per sessione aperta: nome, cosa la sblocca

   ## 1. <Nome del lavoro>
   Riapri: `cd <cartella> && claude --resume <id>`
   - **Dove sei:** fatti, con numeri dove ci sono (test, PR, commit)
   - **Da fare:** azioni concrete, la prima in grassetto
   - **Aspetti:** chi o cosa, se c'è
   - **Prima di iniziare:** passi di preparazione (chiavi SSH, VPN, servizi da avviare), se servono

   ## Chiuso oggi
   - una riga per lavoro finito
   ```

5. **Da approfondire.** Proponi fino a 5 argomenti incontrati oggi che vale la pena studiare con calma: concetti spiegati di corsa, soluzioni adottate senza capirle fino in fondo, strumenti nuovi. Mario sceglie; aggiungi quelli scelti a `~/Dev/bottega/dati/da-approfondire.md` nel formato della skill `/da-approfondire`.

6. **Saluta.** Messaggio breve in chat:
   - quante sessioni restano aperte e la prima cosa da fare domani;
   - **Dopo bottega:** 2 o 3 voci aperte di `da-approfondire.md` adatte al tempo rimasto, più eventuali compiti di amministrazione emersi oggi.
