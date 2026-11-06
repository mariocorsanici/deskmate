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
