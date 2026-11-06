# 02: /whats-on-today lists what changed on the remote since the handoff

**Status:** ready-for-agent

Even with fresh refs, the morning report did not say *what* had moved. The user should see others' work before planning.

- [x] For each active card's repo, after `check.py`, list commits on the remote default/integration branch newer than the handoff's timestamp, with author and subject (e.g. `git log origin/develop --since=<handoff time> --format='%h %an %s'`), and PRs merged in that window when `gh` is available.
- [x] Commits by other people are marked, so "Gio merged #19–#24" is visible at a glance.
- [x] When the list contradicts the handoff's "To do" (work already done), the skill says so before proposing the order.
- [x] Empty windows print one line ("nothing new on the remote"), not one per repo.

## Comments

Implemented 2026-11-06. Local remote-window probe verified other-author metadata, spaced paths, non-develop default, empty intervals and failed-fetch cached reads. Skill instruction review covers reconciliation, combined empty output and unavailable PR coverage. See `docs/testing/daily-loop-tuning.md`; native-agent acceptance remains unclaimed.
