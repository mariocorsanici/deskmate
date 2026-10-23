#!/usr/bin/env python3
"""Riempie in registro.csv i token consumati da ogni lancio delle skill della bottega.

Un lancio va dal comando (/chiudi-bottega, ...) fino al comando successivo
della stessa sessione (qualsiasi /comando) o alla fine della sessione, quindi
comprende anche le risposte di Mario dentro la skill. I token vengono dal
campo usage dei messaggi di Claude nel transcript.

Uso:
  consumi.py                  # tutte le sessioni presenti nel registro
  consumi.py --sessione <id>  # solo una (lo usa l'hook Stop)
"""
import argparse
import csv
import fcntl
import json
import pathlib
import re

DATI = pathlib.Path(__file__).resolve().parent.parent / "dati"
REGISTRO = DATI / "registro.csv"
PROGETTI = pathlib.Path.home() / ".claude" / "projects"
COLONNE = ["data", "ora", "giorno", "evento", "dettaglio", "sessione", "cartella",
           "turni", "token_input", "token_cache", "token_output"]
COMANDO = re.compile(r"^\s*<command-name>/?([^<]+)</command-name>")


def leggi_transcript(percorso):
    """Ritorna i comandi lanciati [(ts, nome)] e i consumi [(ts, input, cache, output)]."""
    comandi, consumi, visti = [], [], set()
    for riga in percorso.open(encoding="utf-8", errors="replace"):
        try:
            r = json.loads(riga)
        except json.JSONDecodeError:
            continue
        ts = r.get("timestamp")
        msg = r.get("message") or {}
        if r.get("type") == "user" and not r.get("isMeta") and isinstance(msg.get("content"), str):
            m = COMANDO.match(msg["content"])
            if m:
                comandi.append((ts, m.group(1).strip()))
        elif r.get("type") == "assistant" and msg.get("usage") and msg.get("id") not in visti:
            visti.add(msg.get("id"))
            u = msg["usage"]
            consumi.append((ts, u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0),
                            u.get("cache_read_input_tokens", 0), u.get("output_tokens", 0)))
    return comandi, consumi


def calcola(sessione, righe):
    trovati = list(PROGETTI.glob(f"*/{sessione}.jsonl"))
    if not trovati:
        return
    comandi, consumi = leggi_transcript(trovati[0])
    usati = set()
    for riga in righe:
        # il k-esimo lancio di una skill nel registro corrisponde al k-esimo nel transcript
        indice = next((i for i, (_, nome) in enumerate(comandi)
                       if nome == riga["evento"] and i not in usati), None)
        if indice is None:
            continue
        usati.add(indice)
        inizio = comandi[indice][0]
        fine = comandi[indice + 1][0] if indice + 1 < len(comandi) else "9999"
        parte = [c for c in consumi if inizio <= c[0] < fine]
        riga["turni"] = str(len(parte))
        for nome, pos in (("token_input", 1), ("token_cache", 2), ("token_output", 3)):
            riga[nome] = str(sum(c[pos] for c in parte))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sessione")
    p.add_argument("--progetti", type=pathlib.Path, help="cartella dei transcript (per i test)")
    a = p.parse_args()
    global PROGETTI
    PROGETTI = a.progetti or PROGETTI
    if not REGISTRO.exists():
        return
    with (DATI / ".registro.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        with REGISTRO.open(newline="") as f:
            righe = list(csv.DictReader(f))
        per_sessione = {}
        for r in righe:
            if r.get("sessione") and not r["evento"].startswith("promemoria"):
                per_sessione.setdefault(r["sessione"], []).append(r)
        for sessione, gruppo in per_sessione.items():
            if a.sessione in (None, sessione):
                calcola(sessione, gruppo)
        with REGISTRO.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=COLONNE, quoting=csv.QUOTE_MINIMAL, extrasaction="ignore")
            w.writeheader()
            w.writerows({k: (r.get(k) or "") for k in COLONNE} for r in righe)


if __name__ == "__main__":
    main()
