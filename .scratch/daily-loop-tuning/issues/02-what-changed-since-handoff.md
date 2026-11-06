# 02: /whats-on-today lists what changed on the remote since the handoff

**Status:** ready-for-agent

Even with fresh refs, the morning report did not say *what* had moved. The user should see others' work before planning.

- [ ] For each active card's repo, after `check.py`, list commits on the remote default/integration branch newer than the handoff's timestamp, with author and subject (e.g. `git log origin/develop --since=<handoff time> --format='%h %an %s'`), and PRs merged in that window when `gh` is available.
- [ ] Commits by other people are marked, so "Gio merged #19–#24" is visible at a glance.
- [ ] When the list contradicts the handoff's "To do" (work already done), the skill says so before proposing the order.
- [ ] Empty windows print one line ("nothing new on the remote"), not one per repo.

## Comments
