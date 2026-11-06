# Agenda: proposta di sviluppo in parallelo

Data: 2026-11-06
Stato: approvata dal cliente il 2026-11-06

## Obiettivo e vincoli

Avviare `feature/agenda` mentre altri due agenti lavorano su
`feature/codex-cli-support` e `feature/daily-loop-tuning`, riducendo le
sovrapposizioni. Il comportamento di prodotto resta quello già descritto in
[spec.md](spec.md); questo documento propone soltanto l'organizzazione.

Ogni agente usa un worktree e un branch distinti. Il checkout principale resta
su `develop`. Un worktree separa i file e l'indice Git, ma non elimina i conflitti
quando due branch modificano lo stesso comportamento.

## Approcci

- **Proposta:** sviluppare subito il motore e i test di agenda; tenere le
  integrazioni condivise in commit distinti e adattarle dopo il lavoro CLI.
  Permette di iniziare senza aspettare e circoscrive i conflitti successivi.
- Implementare subito tutte le modifiche alle skill su ciascun branch: consente
  una validazione completa prima, ma richiede riconciliare tre versioni delle
  stesse istruzioni. Poco adatto all'obiettivo di ridurre i conflitti.

## Primo blocco di lavoro

Ticket 01: `tools/agenda.py` e `tests/test_agenda.py`, standard library Python,
comandi eseguiti con `python3 -I`, dati di prova in directory temporanee.

Mantenere l'interfaccia della specifica: `add`, `day`, `done`, `remove`, `list`,
`is-dev-day`, `archive`; codici 0/1/2/3, con 3 prioritario su 2 per `is-dev-day`;
archivio sotto `data/archive/` e lock `data/.agenda.lock`.

Nessun test deve leggere o modificare i dati personali del checkout installato.

## Secondo blocco e punti di contatto

La nuova `skills/agenda/SKILL.md` puo essere preparata separatamente. I raccordi
in `tools/hook_log.sh`, `install.sh` e README vanno in commit mirati, evitando
riformattazioni e ristrutturazioni non necessarie.

Le modifiche a `skills/whats-on-today/SKILL.md`,
`skills/call-it-a-day/SKILL.md` e `skills/how-did-it-go/SKILL.md` sono i punti di
sovrapposizione maggiori: applicarle come aggiunte circoscritte, in commit
separati dal motore, preservando le responsabilita degli altri branch.

Questa e una proposta di ripartizione, non un accordo gia comunicato agli altri
agenti. Non sono stati inviati messaggi agli altri agenti.

## Integrazione

Seguire la specifica: far atterrare prima `feature/codex-cli-support` su
`develop`, poi aggiornare ciascun feature branch sul risultato. Agenda e daily
loop restano indipendenti: non occorre che uno aspetti l'altro per sviluppare
il proprio nucleo. L'ordine tra loro si decide quando sono pronti.

Il ticket 06 resta successivo: collegare il conteggio dei giorni di sviluppo e
la regola di handoff obsoleto soltanto quando i prerequisiti di entrambi i
branch sono su `develop`. Evitare import o dipendenze da codice ancora presente
solo nel worktree di un altro agente.

Un solo responsabile integra su `develop` alla volta. Dopo ogni integrazione,
eseguire le suite pertinenti insieme e validare le tre skill del ciclo
giornaliero: l'assenza di conflitti Git non prova che i comportamenti concordino.

## Verifica del primo blocco

Coprire formato italiano e inglese, file mancante o danneggiato, preservazione
dei byte non modificati, ambiguita delle ricerche, giorni sovrapposti, finestre
in giorni lavorativi, archiviazione e scritture concorrenti. Aggiornare il
ticket 01 solo con risultati effettivamente verificati.
