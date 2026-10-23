#!/bin/zsh
# Aggiunge una riga a dati/registro.csv (i token li riempie poi consumi.py).
# Uso: registra.sh <evento> [dettaglio] [sessione] [cartella]

python3 -I - "${0:A:h:h}" "$@" <<'PY'
import csv, datetime as dt, fcntl, pathlib, sys
dati = pathlib.Path(sys.argv[1]) / "dati"
registro = dati / "registro.csv"
colonne = ["data", "ora", "giorno", "evento", "dettaglio", "sessione", "cartella",
           "turni", "token_input", "token_cache", "token_output"]
args = (sys.argv[2:] + [""] * 4)[:4]
ora = dt.datetime.now()
with (dati / ".registro.lock").open("w") as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    nuovo = not registro.exists()
    with registro.open("a", newline="") as f:
        w = csv.writer(f)
        if nuovo:
            w.writerow(colonne)
        w.writerow([ora.strftime("%Y-%m-%d"), ora.strftime("%H:%M"),
                    "lun mar mer gio ven sab dom".split()[ora.weekday()], *args, "", "", "", ""])
PY
