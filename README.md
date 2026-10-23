# Bottega

Skill di Claude Code per organizzare la giornata di lavoro: si apre al mattino, si chiude verso le 17, ogni due giorni si fa il punto sul metodo.

## Il giorno tipo

| Quando | Skill | Cosa fa |
|---|---|---|
| 9:00 (promemoria) | `/che-si-fa-oggi` | rilegge le consegne, controlla cosa è cambiato, segnala passaggi saltati, propone l'ordine della giornata e apre le sessioni in iTerm |
| durante il giorno | `/da-approfondire <argomento>` | segna un argomento da studiare dopo |
| lun, mer, ven prima di chiudere | `/com-e-andata` | retrospettiva su organizzazione e metodo, aggiorna `dati/lezioni.md` |
| 17:00 (promemoria) | `/chiudi-bottega` | fotografa le sessioni aperte e scrive `dati/consegne.md` per domani |

Dopo la chiusura: studio degli argomenti da approfondire o amministrazione.

## Installazione

La repo va clonata in `~/Dev/bottega` (le skill cercano lì i file). Poi:

```bash
cd ~/Dev/bottega && claude
```

e lancia `/apri-bottega`: controlla i prerequisiti, esegue `installa.sh` e verifica che tutto risponda. Senza Claude: `./installa.sh`. Per togliere tutto: `./installa.sh --rimuovi` (i dati restano).

Serve macOS con `jq` e `python3`; iTerm per aprire le sessioni nelle tab.

## Cosa installa

- **Skill:** collegamenti da `~/.claude/skills/<nome>` a `skills/<nome>`, quindi le modifiche in repo valgono subito.
- **Hook** in `~/.claude/settings.json`:
  - `UserPromptSubmit` → `strumenti/hook_registro.sh`: scrive in `dati/registro.csv` ogni lancio delle skill;
  - `Stop` → `strumenti/hook_consumi.sh`: riempie i token consumati da ogni lancio (in background).
- **Promemoria** (`launchd/`, installati in `~/Library/LaunchAgents`): 9:00 e 17:00 dal lunedì al venerdì. Se il Mac è in stop all'ora dell'avviso, compare al risveglio se è ancora nella sua fascia (mattina entro le 12, sera 16–21); se è spento, l'avviso salta.

## Struttura

```
skills/                  le skill della giornata
.claude/skills/          /apri-bottega, disponibile lanciando claude nella repo
strumenti/
  sessioni.py            riassunto delle sessioni Claude Code di un periodo
  registra.sh            aggiunge una riga al registro
  consumi.py             calcola i token di ogni lancio dai transcript
  hook_registro.sh       hook UserPromptSubmit
  hook_consumi.sh        hook Stop
  buongiorno.sh          avviso delle 9
  promemoria.sh          avviso delle 17
launchd/                 modelli dei LaunchAgent (__RADICE__ = percorso della repo)
installa.sh              installazione, aggiornamento, rimozione
dati/                    file personali, fuori da git
```

## I dati (`dati/`, non versionati)

- `consegne.md`: stato delle sessioni e cose da fare, riscritto ogni sera; la versione precedente va in `archivio/`.
- `lezioni.md`: registro delle retrospettive, con gli esperimenti di metodo in corso.
- `da-approfondire.md`: argomenti da studiare.
- `registro.csv`: un lancio di skill o un promemoria per riga. Colonne: `data, ora, giorno, evento, dettaglio, sessione, cartella, turni, token_input, token_cache, token_output`. Un lancio va dal comando al `/comando` successivo della stessa sessione, o alla fine della sessione: per conteggi puliti lancia le skill in una sessione dedicata o chiudi con `/clear`.
