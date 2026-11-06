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
