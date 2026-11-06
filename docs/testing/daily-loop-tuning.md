# Daily loop tuning verification

These checks use disposable local repositories and synthetic data. They do not
exercise authenticated Claude/Codex turns or change installed personal data.

## Remote ticket checks (01)

Run `python3 -Werror::ResourceWarning -m unittest discover -s tests -v`.
`test_fetches_quoted_remote_file_without_changing_checkout` creates a local bare
remote on `trunk`, a writer and a reader whose path contains spaces. Both clones
start with `Status: todo`. The writer commits/pushes `Status: done`; the reader
does not pull. The card's check is:

```sh
git -C '<reader with spaces>' show origin/trunk:ticket.md | head -1
```

Before the fix, the automatic fetch split the quoted path and the check returned
the stale `Status: todo`. After the fix, it reports `Status: done`, while the
reader's HEAD and local file remain unchanged. Git commands use argv arrays in
the fixture; no external network is used.

For a failed fetch, the morning skill must treat subsequent remote reads as
cached/unknown, even when `git show` succeeds. A missing branch/path is likewise
unknown, not an empty activity window. This interpretation is an instruction
review; it is not claimed as native-agent behavioral acceptance.

## Morning remote window (02)

Baseline instruction review: the old morning skill ran Checks but had no required
remote commit/PR window before proposing the Handoff's old To do.

The local Git probe on 2026-11-06 used `trunk`, a reader path containing spaces,
and a commit authored by `Other Author <other@example.test>` at
`2026-11-05T10:00:00+01:00`. These commands returned the expected results:

```sh
git -C '<reader with spaces>' symbolic-ref --short refs/remotes/origin/HEAD
# origin/trunk
git -C '<reader with spaces>' log origin/trunk --since=2026-11-04T17:00:00+01:00 --format='%h %aI %an <%ae> %s'
# one commit, Other Author, Complete ticket
git -C '<reader with spaces>' log origin/trunk --since=2026-11-06T12:00:00+01:00 --format=%h
# empty
```

Changing the remote URL to a nonexistent local bare repository made fetch fail,
while `git show origin/trunk:ticket.md` still succeeded. This proves why cached
reads cannot establish freshness. Instruction review covers missing default refs,
standby exclusion, unavailable `gh`/auth, precise PR-time filtering and incomplete
pagination disclosure. No live GitHub request or native-model scenario was run.

## Stale Handoff scenarios (03)

Baseline instruction review: a Wednesday-generated Handoff titled Thursday, read
Friday after an inactive Thursday, passed the old "previous working day" title
check. Creation-time metadata and intervening activity now determine the warning.

Local calendar replay on 2026-11-06, with timezone UTC+01:00:

| Creation → now | Work on intervening dates | Expected inactive count |
| --- | --- | --- |
| Wed 04 17:00 → Fri 06 09:00 | none (or reminder/end rows only) | 1 (Thursday) |
| Thu 05 17:00 → Fri 06 09:00 | none | 0 |
| Wed 04 17:00 → Fri 06 09:00 | Thursday Checkpoint | 0 |
| Wed 04 23:30 at UTC−02:00 → Fri 06 09:00 local | none | 0 (creation is Thursday locally) |
| Fri 06 17:00 → Mon 09 09:00 | none | 2 (Saturday and Sunday) |

The date arithmetic was replayed with Python's timezone-aware `datetime`. Skill
instruction review additionally covers missing metadata (mtime, marked estimated),
future/unreadable timestamps or missing logs (unknown), current Checks failing
(current fact unknown), and retaining the weekday retrospective rule. No claim of
native-agent adherence is made by this arithmetic/instruction verification.

## Skill boundaries and CSV integrity (04)

Run `python3 -Werror::ResourceWarning -m unittest discover -s tests -v`.
The new usage/CSV scenarios were run before implementation and exposed the missing
marker boundary, missing scope and data-root override, legacy header/extension
loss, and malformed transcript handling. The existing remote-check regression
continued to pass. Synthetic fixtures cover:

- explicit end followed by unrelated work; no marker; consecutive/repeated skills;
- a missing first marker, late marker, different session/folder, invalid/naive or
  early timestamps, timezone offsets and native message-ID deduplication;
- legacy CSV upgrades, unknown/provider columns, precise end timestamps, invalid
  CSV preservation and concurrent append/recompute blocked on the same lock.

All fixture data goes to temporary roots. Skill completion instructions were
reviewed for current-session attribution and unfinished interactive work; native
runtime adherence has not been tested. Measurements exclude final prose generated
after the explicit marker and are not whole-interaction billing totals.
