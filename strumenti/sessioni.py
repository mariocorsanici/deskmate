#!/usr/bin/env python3
"""Riassunto testuale delle sessioni Claude Code attive in un intervallo di giorni.

Legge i transcript in ~/.claude/projects/*/*.jsonl (solo sessioni principali,
non i subagent) e stampa, per ogni sessione toccata nel periodo, cartella,
orari, comando per riaprirla e gli ultimi messaggi di testo.

Uso:
  sessioni.py                      # sessioni toccate oggi, ultimi 8 messaggi
  sessioni.py --da 2026-10-21      # dal giorno indicato a oggi
  sessioni.py --messaggi 40        # più messaggi per sessione (retrospettiva)
"""
import argparse
import datetime as dt
import json
import pathlib
import re

PROGETTI = pathlib.Path.home() / ".claude" / "projects"
COMANDO = re.compile(r"<command-name>(.*?)</command-name>.*?(?:<command-args>(.*?)</command-args>)?", re.S)


def testo_utente(contenuto):
    if isinstance(contenuto, list):
        parti = [b.get("text", "") for b in contenuto if b.get("type") == "text"]
        contenuto = "\n".join(parti)
    if not contenuto:
        return None
    m = COMANDO.search(contenuto)
    if m:
        return f"{m.group(1)} {m.group(2) or ''}".strip()
    if contenuto.lstrip().startswith("<"):
        return None
    return contenuto


def testo_assistente(contenuto):
    if isinstance(contenuto, str):
        return contenuto
    return "\n".join(b.get("text", "") for b in contenuto if b.get("type") == "text") or None


def leggi(percorso):
    s = {"id": percorso.stem, "cwd": None, "inizio": None, "fine": None, "messaggi": []}
    for riga in percorso.open(encoding="utf-8", errors="replace"):
        try:
            r = json.loads(riga)
        except json.JSONDecodeError:
            continue
        if r.get("isSidechain") or r.get("isMeta") or r.get("type") not in ("user", "assistant"):
            continue
        s["cwd"] = s["cwd"] or r.get("cwd")  # cartella di partenza: è quella da cui si fa --resume
        ts = r.get("timestamp")
        if ts:
            s["inizio"] = s["inizio"] or ts
            s["fine"] = ts
        contenuto = r.get("message", {}).get("content")
        testo = testo_utente(contenuto) if r["type"] == "user" else testo_assistente(contenuto)
        if testo:
            s["messaggi"].append(("TU" if r["type"] == "user" else "CLAUDE", ts, testo.strip()))
    return s


def ora_locale(ts):
    return dt.datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().strftime("%d/%m %H:%M")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--da", default=dt.date.today().isoformat(), help="primo giorno, AAAA-MM-GG")
    p.add_argument("--messaggi", type=int, default=8, help="ultimi N messaggi per sessione")
    p.add_argument("--taglio", type=int, default=700, help="caratteri massimi per messaggio")
    a = p.parse_args()

    soglia = dt.datetime.combine(dt.date.fromisoformat(a.da), dt.time()).timestamp()
    file = sorted((f for f in PROGETTI.glob("*/*.jsonl") if f.stat().st_mtime >= soglia),
                  key=lambda f: f.stat().st_mtime)
    for f in file:
        s = leggi(f)
        utente = [m for m in s["messaggi"] if m[0] == "TU"]
        if not utente or dt.datetime.fromisoformat(s["fine"].replace("Z", "+00:00")).timestamp() < soglia:
            continue
        print("=" * 80)
        print(f"SESSIONE {s['id']}")
        print(f"cartella: {s['cwd']}")
        print(f"attiva:   {ora_locale(s['inizio'])} -> {ora_locale(s['fine'])}  ({len(utente)} richieste)")
        print(f"riapri:   cd {s['cwd']} && claude --resume {s['id']}")
        print(f"prima richiesta: {utente[0][2][:300]}")
        print("-" * 80)
        for chi, ts, testo in (s["messaggi"][-a.messaggi:] if a.messaggi else []):
            corto = testo if len(testo) <= a.taglio else testo[: a.taglio] + " […]"
            print(f"[{ora_locale(ts)}] {chi}: {corto}\n")


if __name__ == "__main__":
    main()
