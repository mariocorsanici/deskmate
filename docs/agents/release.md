# Releases, deploy and rollback

How the installed Deskmate is kept separate from development work, and how a
release reaches it.

## Branches

- `main`: the released line. A release reaches it only after a stable period
  on `develop`, and is tagged there.
- `develop`: integration and trial; the installed copy follows it.
- `feature/…`, `fix/…`, `docs/…`, `hotfix/…`: one coherent effort each.
  Dependent changes that are not releasable on their own stay on one branch,
  and it is merged into `develop` only when the whole effort is done.

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
| `v0.2.0` (2026-11-23) | Agenda, Daily-loop tuning and follow-ups, after one week of use | unchanged: fast-forward `main`, no upgrade step |
| next, not assigned | Whatever brings a user-facing change; it also carries the removal of the unused calendar and Slack reminder channels and the CI | `data/config.json` may only list the `mac` channel: `./install.sh` refuses any other |

One risky change per release: a release that changes the installation (such
as ROADMAP item 3) carries nothing else, so if it misbehaves the cause is the
migration.

## Deferred

Moving the installed copy and the data out of `~/Dev` is not supported yet:
the skills name `~/Dev/mc_dev/deskmate` directly, and the hooks do not receive
`DESKMATE_DATA_DIR`. See `ROADMAP.md`, items 2 and 3. The checklist for the
dropped Codex release is in this file as of `35ce1ef`.
