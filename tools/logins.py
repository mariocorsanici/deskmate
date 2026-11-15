#!/usr/bin/env python3
"""Checks the logins the projects need, so they can all be done at the start of the day.

A project card lists them in a "## Logins" section, one per line:
  - ssh-key ~/.ssh/<key>   the key is loaded in the SSH agent (fingerprint in `ssh-add -l`)
  - gcloud                 `gcloud auth print-access-token` succeeds
  - gcloud-adc             `gcloud auth application-default print-access-token` succeeds
  - 1password              `op whoami` succeeds; otherwise a warning, not a failure: with the
                           desktop-app integration it reports "not signed in" until a command
                           reads a secret, and Touch ID shows up then

Read-only: only exit codes are used, tokens go to /dev/null and are never printed, each check
has a short timeout, and the fix commands are only printed, never run.

Usage:
  logins.py                every card whose state is not closed or standby
  logins.py <card> ...     these cards: a path or a project name, as for check.py

Prints one JSON object: {"logins": [{login, projects, status, detail, fix}], "all_ok": bool}
status: ok | missing | warning | unavailable (CLI or key file not found) | unknown (login type).
Logins are deduplicated across cards, in order of first appearance.
"""
import json
import os
import pathlib
import shutil
import signal
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import check  # noqa: E402

TIMEOUT = 5
FIX = {
    'gcloud': 'gcloud auth login',
    'gcloud-adc': 'gcloud auth application-default login',
    '1password': 'op vault list >/dev/null',
}
PROBE = {
    'gcloud': ['gcloud', 'auth', 'print-access-token'],
    'gcloud-adc': ['gcloud', 'auth', 'application-default', 'print-access-token'],
    '1password': ['op', 'whoami'],
}


def run(argv, keep_output=False):
    """(exit code or 'timeout', stdout if kept). Never prompts: no stdin, own process group."""
    try:
        proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                stdout=subprocess.PIPE if keep_output else subprocess.DEVNULL,
                                text=True, start_new_session=True)
    except OSError:
        return 'unavailable', ''
    try:
        out, _ = proc.communicate(timeout=TIMEOUT)
        return proc.returncode, out or ''
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        return 'timeout', ''


def probe(kind, target):
    """(status, detail, fix) for one login."""
    if kind == 'ssh-key':
        key = pathlib.Path(target).expanduser() if target else None
        if key is None or not (key.exists() or key.with_name(key.name + '.pub').exists()):
            return 'unavailable', 'key file not found', ''
        if not shutil.which('ssh-add') or not shutil.which('ssh-keygen'):
            return 'unavailable', 'ssh-add not found', ''
        public = key.with_name(key.name + '.pub')
        code, out = run(['ssh-keygen', '-lf', str(public if public.exists() else key)], keep_output=True)
        parts = out.split()
        if code != 0 or len(parts) < 2:
            return 'unavailable', 'cannot read the key fingerprint', ''
        code, loaded = run(['ssh-add', '-l'], keep_output=True)
        if code == 0 and parts[1] in loaded.split():
            return 'ok', '', ''
        detail = 'timeout' if code == 'timeout' else 'not loaded in the SSH agent'
        return 'missing', detail, f'ssh-add {key}'
    if kind not in PROBE:
        return 'unknown', f'unknown login type: {kind}', ''
    if not shutil.which(PROBE[kind][0]):
        return 'unavailable', f'{PROBE[kind][0]} not found', ''
    code, _ = run(PROBE[kind])
    if code == 0:
        return 'ok', '', ''
    detail = 'timeout' if code == 'timeout' else f'exit {code}'
    if kind == '1password':
        return 'warning', detail + ': Touch ID will show up at the first secret read', FIX[kind]
    return 'missing', detail, FIX[kind]


def main():
    args = sys.argv[1:]
    cards = check.select(args)
    wanted = {}
    for card in cards:
        text = card.read_text(encoding='utf-8')
        state = check.state_of(text)
        if not args and state in ('closed', 'standby'):
            continue
        name = check.title(text, card)
        for line in check.section(text, 'Logins').splitlines():
            line = line.strip()
            if line.startswith('- ') and line[2:].strip():
                login = ' '.join(line[2:].split())
                projects = wanted.setdefault(login, [])
                if name not in projects:
                    projects.append(name)
    logins = []
    for login, projects in wanted.items():
        kind, _, target = login.partition(' ')
        status, detail, fix = probe(kind, target.strip())
        logins.append({'login': login, 'projects': projects, 'status': status, 'detail': detail, 'fix': fix})
    print(json.dumps({'logins': logins, 'all_ok': all(l['status'] in ('ok', 'warning') for l in logins)},
                     ensure_ascii=False))


if __name__ == '__main__':
    main()
