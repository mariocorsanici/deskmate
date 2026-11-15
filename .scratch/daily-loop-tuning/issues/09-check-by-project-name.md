# 09: `check.py` accepts a project name, not only a card path

**Status:** done (hotfix on develop, `51ba159`)

On 2026-11-09, `/whats-on-today` ran `python3 -I tools/check.py vlm` to recheck one project before opening its session. It crashed with a traceback:

```
FileNotFoundError: [Errno 2] No such file or directory: 'vlm'
```

`check.py` treats every argument as a card path (`pathlib.Path(a).expanduser()`), but the skills write `check.py <card>` (`whats-on-today` step 4, `checkpoint` step on Checks), which reads naturally as a project name. The full path worked:
`check.py ~/.claude/projects/-Users-mario-corsanici-domyn-com-Dev-domyn-dev-vlm-demo-builder/memory/project-card.md`.

- [x] An argument that is an existing file is used as a card path, as today.
- [x] Otherwise it is matched, case-insensitively, against each card's folder key under `~/.claude/projects/*/memory/project-card.md` and its title. One match runs that card. Several matches or none: print the candidates (title and path) and exit non-zero, with no traceback.
- [x] `check.py vlm`, `check.py fleet` and `check.py basler` work on the current cards. A name that matches more than one card (e.g. both Fleet cards, until the old one is closed) lists them. Closed cards count only when no open card matches; on 2026-11-15 `vlm` and `fleet` resolve to the apps-monorepo card, `basler` to aigo-controller.
- [x] The skills that mention `check.py <card>` say that a project name or a card path both work.
- [x] Tests: fake card folders, covering a path, a single match, several matches and no match.

## Comments
