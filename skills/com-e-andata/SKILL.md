---
name: com-e-andata
description: Retrospettiva su organizzazione e metodo degli ultimi giorni; aggiorna lezioni.md.
disable-model-invocation: true
---

# Com'è andata

Una **retrospettiva** sul *come* si è lavorato negli ultimi giorni, non sul contenuto tecnico: organizzazione, metodo, uso di Claude. Si fa lunedì, mercoledì e venerdì, prima di `/chiudi-bottega`. I file di dati sono in `~/Dev/bottega/dati/`. Scrivi in italiano semplice.

## Passi

1. **Periodo.** Dal giorno dopo l'ultima voce di `~/Dev/bottega/dati/lezioni.md` a oggi; se `lezioni.md` non ha ancora voci, gli ultimi 3 giorni.

2. **Raccogli.** Esegui `python3 -I ~/Dev/bottega/strumenti/sessioni.py --da <inizio> --messaggi 60 --taglio 400` e leggi le consegne del periodo in `~/Dev/bottega/dati/archivio/` e `consegne.md`: sono il piano, i transcript sono ciò che è successo. `~/Dev/bottega/dati/registro.csv` dice quando sono state lanciate le skill e come hai risposto ai promemoria.

3. **Analizza** con queste lenti. Ogni osservazione cita la prova: sessione, ora, cosa è successo.
   - **Ritmo:** dal registro, giorni senza apertura o chiusura, retrospettive saltate, promemoria rimandati o ignorati.
   - **Piano e realtà:** cosa era nelle consegne ed è stato fatto, rimandato, dimenticato.
   - **Rilavorazioni:** false partenze, risposte ritrattate, note vecchie prese per buone, lavoro rifatto.
   - **Attese e blocchi:** tempo fermo ad aspettare persone, permessi, accessi.
   - **Cambi di contesto:** sessioni in parallelo, interruzioni, lavori ripresi più volte.
   - **Uso di Claude:** richieste vaghe che hanno chiesto chiarimenti, cose che Claude poteva fare da solo o che conveniva fare a mano.
   - **Cosa ha funzionato:** da ripetere.
   Fatto quando ogni lente ha almeno un'osservazione con prova, oppure una riga "niente da segnalare".

4. **Esperimenti precedenti.** Per ogni esperimento dell'ultima voce: è stato fatto? Ha aiutato? Decidi se tenerlo, cambiarlo o lasciarlo. Confronta anche con le voci più vecchie: un problema visto due volte o più è **ricorrente**.

5. **Parlane.** Presenta a Mario le 3–5 osservazioni più forti, ricorrenti per prime, e chiedi la sua lettura: è una conversazione, la sua opinione conta più dei transcript. Concordate 1–3 esperimenti per i prossimi giorni, concreti e verificabili ("apro una sessione per progetto", non "essere più ordinato").

6. **Registra.** Aggiungi in fondo a `lezioni.md`:

   ```markdown
   ## <AAAA-MM-GG> (periodo <inizio> → <fine>)
   **Ha funzionato:** …
   **Da migliorare:** … (segna *ricorrente* dove serve)
   **Esperimenti precedenti:** <nome> → tenuto / cambiato / lasciato, perché
   **Esperimenti in corso:**
   - …
   ```

   Poi ricorda che `/chiudi-bottega` è il passo successivo.
