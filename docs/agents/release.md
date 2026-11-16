# Releases, deploy and rollback

How the installed Deskmate is kept separate from development work, and how a
release reaches it. Branch roles (`main`, `develop`, `feature/*`) are in
`development-workflow.md`, which arrives on `develop` with the Codex branch.

## Rules

1. **One installed copy: `~/Dev/mc_dev/deskmate`.** Skills, hooks and
   reminders point into it, and the personal data lives in its `data/`. Any
   change to its files is a deploy. It only receives explicit deploys and
   rollbacks, never direct edits.
2. **Develop only in worktrees**, `~/Dev/mc_dev/deskmate-<effort>`, one branch
   each (`feature/…`, `fix/…`, `docs/…`; `hotfix/…` for urgent fixes to the
   installed version). Tests run against temporary data (`DESKMATE_DATA_DIR`),
   never the real `data/`.
3. **Every release on `main` has a tag** (`vMAJOR.MINOR.PATCH`; while `0.x`,
   a minor bump may change installation) and a short note in its tag message:
   what changes for the user, and whether an upgrade step is required.

## Deploy and rollback

The installed copy follows the line under trial (today `develop`).

- **Deploy:** merge the reviewed branch into `develop` from the installed copy,
  `git -C ~/Dev/mc_dev/deskmate merge --ff-only <branch>` (or `git pull`).
  Skills and hooks use the new files at their next run. Rerun `./install.sh`
  only when the change touches `install.sh`, hooks or reminder schedules.
- **Rollback:** copy `data/` first, then
  `git -C ~/Dev/mc_dev/deskmate switch --detach <previous tag>` and rerun
  `./install.sh` if the installation differs. Rolling back from `develop` to
  `v0.1.0` drops the `usage_scope` column from `log.csv`; the rest of the data
  is unchanged.

## Release plan

| Version | Content | Installation |
|---|---|---|
| `v0.1.0` (2026-11-16) | Claude-only Daily loop, standby, check fetch, L09 hotfix | in place, symlinks to the installed copy |
| `v0.2.0` | Agenda, Daily-loop tuning and follow-ups, after one week of use | unchanged: fast-forward `main`, no upgrade step |
| `v0.3.0` | Codex CLI support (`feature/codex-cli-support`) | **changes**: requires `deskmate setup` (upgrade checklist below) |

One risky change per release: if `v0.3.0` misbehaves, the cause is the
migration or Codex, not the Agenda.

## v0.3.0 upgrade checklist

Run once, at the end of a working day, after `/call-it-a-day`.

1. **Before merging.** Merge `develop` into the feature again, port any fixes
   made since (skills there call `deskmate …` instead of tool paths), run the
   full suite on Python 3.14 and the macOS system Python, and rehearse steps
   3–5 and the rollback in an isolated `HOME`.
2. **Back up.** Copy `data/`, `~/.claude/settings.json`,
   `~/Library/LaunchAgents/com.deskmate.*.plist` and every
   `~/.claude/projects/*/memory/project-card.md` (with their folder keys)
   outside the repo. Setup turns those cards into symlinks to `data/projects/`.
3. **Merge and tag** the feature into `develop`.
4. **Set up from the installed copy:**
   `cd ~/Dev/mc_dev/deskmate && bin/deskmate setup`. Hooks are written with the
   absolute path of the checkout that runs setup; running it from a worktree
   would move the installation there. Setup installs `~/.local/bin/deskmate`,
   replaces the hooks, moves the project cards to `data/projects/` (symlinks
   left in `~/.claude/projects/*/memory/`), migrates `log.csv` with a backup,
   rewrites the reminders and links the skills for Codex if chosen.
5. **Verify** the next morning: `/whats-on-today` in Claude and
   `$whats-on-today` in Codex each add one row to `data/log.csv` with their
   provider; `deskmate check` lists every card; both reminders are loaded
   (`launchctl print gui/$(id -u)/com.deskmate.morning`).
6. **Rollback, if needed:** `deskmate remove` (keeps data), restore the step 2
   copies (replacing the card symlinks with the saved files),
   `git switch --detach v0.2.0`, `./install.sh`. Cards written after the
   upgrade exist only in `data/projects/`: copy their current text over the
   saved ones first.
7. Promote to `main` with the tag after a stable period.

## Deferred

Moving the installed copy and the data out of `~/Dev` (for example a clone
pinned to a tag, with data elsewhere) is not supported end to end yet:
reminders receive `DESKMATE_DATA_DIR`, but the Claude and Codex hooks use
`<repo>/data`. See `ROADMAP.md`.
