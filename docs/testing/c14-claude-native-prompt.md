# Prompt per i test manuali Claude-only di C14

Preparato su richiesta dell'utente e conservato per la prossima sessione.
I test Claude non sono stati avviati: questo è un prompt da copiare in Claude
Code, non un'autorizzazione a eseguirli in background. L'autorizzazione contenuta
nel blocco si applica quando l'utente lo invia per avviare la prova. Il gruppo
cross-provider resta sospeso.

Aprire Claude Code nel worktree `deskmate-codex` e inviare:

```text
Completa il gruppo di test manuali Claude-only del ticket C14 di Deskmate.

Autorizzo le richieste native Claude necessarie a questa prova. Il gruppo cross-provider resta sospeso: non avviare Codex e non eseguire switch tra provider.

Contesto:
- Repository/worktree: /Users/mario.corsanici@domyn.com/Dev/mc_dev/deskmate-codex
- Branch previsto: feature/codex-cli-support
- Ultimo commit noto: 8ab2f78, correzione dei timestamp Checkpoint.
- C14-CODEX-01 è risolto; C14-CODEX-02, relativo allo storico SQLite Codex dopo la chiusura, resta aperto.

Prima di iniziare:
1. Leggi AGENTS.md, CLAUDE.md, docs/agents/development-workflow.md, il ticket .scratch/provider-neutral-cli/issues/14-clean-cut-and-daily-loop-validation.md e docs/testing/daily-loop.md.
2. Verifica branch, commit e modifiche locali; preserva il lavoro esistente.
3. Prepara un progetto temporaneo non sensibile, con HOME, configurazione nativa Claude e DESKMATE_DATA_DIR isolati. Disabilita i canali dei promemoria nell'ambiente di prova.
4. Usa la normale autenticazione della CLI senza leggere, stampare o salvare valori delle credenziali. Se serve un intervento umano per autenticazione o permessi, indica precisamente quale.

Esegui prove native reali, distinguendole dai controlli sintetici:

- Setup Claude-only due volte, verificando idempotenza e conservazione delle preferenze. Invoca anche /setup nella sessione nativa.
- Verifica dal catalogo nativo la discovery delle cinque skill operative; i collegamenti su disco da soli non bastano.
- Segui le normali approvazioni del runtime e degli hook, senza bypass dei permessi.
- Esegui /whats-on-today nel progetto isolato.
- Esegui /study-later con un argomento innocuo e verifica il salvataggio.
- Esegui /checkpoint: controlla il salvataggio della scheda, revisione, Provider, ID nativo e cartella. Inserisci ed esegui un Check di sola lettura su un file di prova.
- Verifica gli eventi reali degli hook e il logging, inclusa l'attribuzione Claude e l'identità della sessione.
- Chiudi completamente la sessione e riaprila con resume. Verifica stesso ID, cartella, proprietà della scheda e Check.
- Esegui /how-did-it-go: prima evidenze durevoli e candidati, poi pausa per la selezione. Seleziona esplicitamente solo la sessione di prova; verifica confine del Checkpoint, limiti, copertura, omissioni e avvisi. Completa la conversazione e salva lessons.md.
- Esegui /call-it-a-day e verifica l'Handoff, i Check aggiornati e le informazioni di ripresa.

Usa le skill installate senza suggerire nei messaggi un formato del timestamp. Conserva le prime osservazioni di ogni errore e distingui eventuali workaround dai risultati iniziali. Puoi prendere le decisioni innocue della conversazione di prova, come selezionare la sessione temporanea e concordare un esperimento.

Registra date, commit, versioni CLI, comandi, ID nativi, revisioni, risultati e limiti in:
docs/testing/c14-claude-native-<data>.md
docs/testing/c14-claude-native-<data>.json

Aggiorna la checklist C14 con le sole verifiche effettivamente eseguite. Segnala separatamente eventuali prove desktop, calendario o lancio tramite iTerm non verificate.

Questa sessione serve a eseguire e documentare i test: registra eventuali difetti senza modificare l'implementazione. Non dichiarare C14 completa mentre restano il gruppo cross-provider e C14-CODEX-02. Non eseguire push o merge.
```

Stato e lavoro residuo sono nel
[punto di ripresa del tracker](../superpowers/plans/2026-11-09-development-tracker.md#resume-checkpoint--2026-11-12).
