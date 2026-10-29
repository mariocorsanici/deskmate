# Scanner locali di segreti per bundle di trasferimento temporanei

_Ricerca aggiornata al 29 ottobre 2026. Fonti: documentazione e codice ufficiali dei progetti._

## Conclusione

Per un piccolo bundle testuale da controllare prima del passaggio tra Claude Code e Codex CLI, **Gitleaks è il gate primario più semplice**: ha un comando `stdin` esplicito, distribuzioni binarie, output JSON e un exit code configurabile. **`detect-secrets --no-verify` è una buona seconda scansione indipendente**, soprattutto se il bundle esiste già come file temporaneo; il suo output baseline non conserva in chiaro i valori candidati.

Usarli insieme può aumentare la copertura, ma anche il rumore. Nessuno dei due dimostra che un bundle sia privo di segreti: sono difese euristiche aggiuntive, soggette a falsi negativi e falsi positivi. Il controllo non protegge inoltre da log, cronologia della shell, file temporanei mal protetti o conservazione effettuata dagli strumenti a valle.

## Confronto

| Aspetto | Gitleaks | `detect-secrets` |
|---|---|---|
| Esecuzione locale/offline | La scansione è locale e offre le modalità `git`, `dir` e `stdin`. Una volta installato, non è documentata alcuna dipendenza da un servizio remoto per la scansione. | Il motore gira localmente, ma per impostazione predefinita può tentare la verifica di alcuni candidati tramite chiamate di rete. Per un controllo realmente offline va passato `--no-verify` (`-n`). |
| File e stdin | Scansiona un singolo file o una directory con `dir` e contenuto in pipe con `stdin`. È il supporto più diretto per un bundle effimero. | `scan` accetta path; per file non tracciati da Git va usato `--all-files`. Offre anche `--string`, ma non documenta una modalità stdin per contenuto grezzo: un file temporaneo con permessi restrittivi è l'interfaccia più chiara. |
| Output machine-readable | Report JSON, CSV, JUnit, SARIF o template; `--report-path -` invia il report a stdout. `--exit-code` consente di riservare un codice specifico ai rilevamenti. | `detect-secrets scan` emette su stdout una baseline JSON. `detect-secrets-hook --json` offre JSON per la modalità hook. La baseline identifica i candidati tramite hash anziché registrarne il valore in chiaro. |
| Installazione e dipendenze | Homebrew, immagini Docker, build da sorgente o binari precompilati per più piattaforme. Il binario di release evita una dipendenza runtime da Go; Go serve per la build da sorgente. | `pip install detect-secrets` o Homebrew. È un pacchetto Python e dichiara dipendenze da `pyyaml` e `requests`; word list e gibberish detector aggiungono dipendenze opzionali. |
| Regole e rumore | Regole basate su regex, gruppi/entropia, keyword e allowlist configurabili. Entropia e pattern generici possono segnalare fixture, esempi e identificatori casuali; allowlist troppo larghe possono invece nascondere un segreto reale. | Combina plugin regex, entropia e keyword. La documentazione ammette un compromesso precisione/recall e fornisce filtri, soglie e allowlist per ridurre i falsi positivi; la regolazione può introdurre falsi negativi. |
| Limiti notevoli | Rileva ciò che le regole/configurazioni conoscono. Decodifica ricorsiva e scansione degli archivi sono controllate da flag e non vanno date per scontate; l'output può essere sensibile se non redatto. L'exit code predefinito `1` copre sia leak sia errori. | Le caveat ufficiali citano esplicitamente segreti multilinea e password predefinite che non attivano il `KeywordDetector`. La verifica remota riduce alcuni falsi positivi ma è incompatibile con il requisito offline e può esporre un candidato a un endpoint esterno. |

Fonti ufficiali: [README di Gitleaks](https://github.com/gitleaks/gitleaks/blob/master/README.md), [release/binary di Gitleaks](https://github.com/gitleaks/gitleaks/releases), [README di `detect-secrets`](https://github.com/Yelp/detect-secrets/blob/master/README.md), [design delle baseline di `detect-secrets`](https://github.com/Yelp/detect-secrets/blob/master/docs/design.md), [verifica dei plugin](https://github.com/Yelp/detect-secrets/blob/master/docs/plugins.md), [dipendenze Python](https://github.com/Yelp/detect-secrets/blob/master/setup.py).

## Uso consigliato

### Gate primario: Gitleaks su stdin

```bash
gitleaks stdin \
  --no-banner \
  --redact=100 \
  --report-format json \
  --report-path - \
  --exit-code 2 < "$bundle_path"
```

Questa forma non crea una seconda copia del bundle. Convenzione suggerita: `0` significa nessun finding, `2` indica almeno un finding, mentre altri codici vanno trattati come errore di esecuzione. Il report JSON va comunque analizzato e non archiviato senza necessità. Il flag `--redact=100` è importante perché il formato dei finding include normalmente campi che possono contenere il match o il segreto; la documentazione lo descrive per log e stdout.

Se l'input è già un file temporaneo e serve preservarne il nome nel finding:

```bash
gitleaks dir "$bundle_path" \
  --no-banner \
  --redact=100 \
  --report-format json \
  --report-path - \
  --exit-code 2
```

I comandi, i formati di report, la redazione e i codici d'uscita sono documentati nel [README ufficiale di Gitleaks](https://github.com/gitleaks/gitleaks/blob/master/README.md). Il codice ufficiale documenta anche `-` come destinazione stdout di `--report-path` nella [definizione della CLI](https://github.com/gitleaks/gitleaks/blob/master/cmd/root.go).

### Seconda opinione: `detect-secrets` offline

```bash
detect-secrets scan \
  --no-verify \
  --all-files \
  "$bundle_path" > "$detect_report_path"

jq -e '.results | length == 0' "$detect_report_path"
```

`scan` crea uno snapshot JSON: il gate deve quindi controllare che `results` sia vuoto, non limitarsi al successo del processo. `--no-verify` è indispensabile per evitare le verifiche via rete documentate dal progetto. L'alternativa `--string` mette il contenuto nell'argomento del processo e può farlo finire nella cronologia della shell o nell'elenco processi; per un segreto potenziale è preferibile non usarla.

Il comportamento di `scan`, `--all-files`, `--no-verify` e i limiti dichiarati sono nel [README ufficiale](https://github.com/Yelp/detect-secrets/blob/master/README.md). La rappresentazione hash della baseline è descritta nel [design ufficiale](https://github.com/Yelp/detect-secrets/blob/master/docs/design.md).

## Precauzioni operative

- Creare l'eventuale bundle con permessi `0600`, in una directory temporanea privata, e limitarne la vita al tempo strettamente necessario.
- Evitare di stampare il bundle o report non redatti nel terminale, nei log CI o nella cronologia della shell.
- Considerare qualunque finding come motivo per fermare il trasferimento e verificare; se il valore è reale, revocarlo o ruotarlo, non limitarsi a rimuoverlo dal testo.
- Tenere aggiornati scanner e regole. Un risultato pulito significa soltanto “nessuna regola attiva ha trovato un candidato”.
- Affiancare controlli deterministici specifici del contesto quando possibile, per esempio il divieto esplicito di file `.env`, chiavi private PEM o prefissi di token interni noti.

## Valutazione finale

Per questo caso d'uso conviene partire con Gitleaks perché stdin riduce le copie temporanee e JSON più exit code configurabile rendono semplice un gate locale. `detect-secrets --no-verify` aggiunge diversità nelle euristiche e una baseline che non conserva i valori grezzi, al costo di richiedere un file/path e di dover interpretare `results`. L'esecuzione in sequenza è una difesa ragionevole, non una garanzia assoluta.
