# Provider switch and protected-transfer verification

Verified 2026-11-09. C09 and C10 are implemented on `feature/codex-cli-support`.
The owner requested stopping after C10's commit; C11–C14 have not been started.

## Evidence

- Baseline before C09: 157 tests passed with ResourceWarnings as errors.
- C09: six public command/PTY tests observed failing before implementation;
  full suite 163/163 passed before commit `b81b268`.
- Final C10 full suite: **180/180 tests pass**, no skips, ResourceWarnings as errors.
- The **23 switch/transfer tests** also pass on macOS system Python 3.9.6.
- Whitespace checks pass.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -Werror::ResourceWarning -m unittest discover -s tests -q
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -Werror::ResourceWarning -m unittest tests.test_provider_switch tests.test_transfers -q
git diff --check
```

Automated tests use temporary homes/data, synthetic transcripts and fake native
executables. Both switch directions are exercised. No installed personal state,
authenticated model requests or real iTerm/Provider launches were used.

The command/PTY tests cover unavailable source Providers/transcripts, new target
identity, current Checks, conservative possible-overlap warning, cancellation,
failed target submission, native-hook ownership, no noninteractive consent bypass,
stale-card refusal, redaction/counts, configured delta limits, exact final bundle
size, private modes, path-only launch, content-free audit, matching-target one-use
consumption, expiry, canonical macOS path aliases and preservation of unrelated
files/symlinks. Later normal commands clean expired managed bundles; explicit
previews, dry runs and delta inspection preserve their read-only contract.

## Independent review and fix pass

One independent reviewer inspected C09 plus the C10 working tree and independently
ran the original 16 focused tests. Four Important issues were reproduced before
their corrections:

1. Incomplete quoted passwords, including a closing quote lost to bounded delta
   truncation, were previously sent unchanged; escaped quotes leaked suffixes.
   A quote/escape-aware assignment scan now redacts complete values and blocks
   incomplete/uncertain values. Card, escaped single/double-quote and actual
   character-truncated transcript regressions were observed RED, then GREEN.
2. Prefixed environment names such as `DATABASE_PASSWORD`,
   `AWS_SECRET_ACCESS_KEY` and `OPENAI_API_KEY` bypassed exact-key matching.
   Credential-name classification now handles prefixed, separated and camel-case
   keys. Public card/Check-output/delta regressions prove the synthetic values
   are absent from approved bundles and audit records.
3. Relative Checks inherited the caller's directory. Checks now run in the
   canonical selected Project directory; the public `pwd` regression first
   reported the checkout, then correctly reported the Project.
4. Orphan cleanup ran only on another approved switch or an explicit cleanup.
   Successful later normal commands now invoke cleanup. The RED/GREEN regression
   verifies old managed bundles disappear while fresh bundles, symlinks and
   unrelated files survive, and previews/dry runs remain immutable.

Additional RED/GREEN corrections fixed macOS `/var` versus `/private/var` parent
normalization, use of configured limits in the switch, exact final bundle sizing,
and Python 3.9's lack of `Path.stat(follow_symlinks=...)`; `lstat()` preserves the
same no-follow check on supported system Python. The final complete suite and
system-Python focused suite verify the fix pass. No second review was run.

## Deferred Minor

The generic card-and-Checks warning still describes transcript context as
unavailable even when a healthy delta is included. The manifest and actual delta
coverage/counts are accurate. Refine that wording during the later clean cut;
this does not change transfer content or consent enforcement.

## Scope decisions

- The temporary bundle is approved interactively, contains locally redacted
  context and is handed off by path only. There is no unattended consent flag.
- Redaction handles common credentials conservatively, not every possible
  secret format. Uncertain recognized values block rather than claiming a clean
  transfer. Native authenticated acceptance remains C14 work.
- Private ownership, no-follow reads and inode comparisons constrain filesystem
  replacement. No claim of defence against an adversarial same-user process is
  made; no separate-privilege exploit was established by review.
- Cleanup deletes only valid, private, managed regular files older than one hour.
  Malformed/unattributable matching files are preserved rather than treating a
  filename alone as deletion authority.
- Shell Checks retain the specification's trusted read-only convention; a
  structured allowlist is future work. A TTY supplies the interactive consent
  flow; stronger human-versus-automation authentication is not specified.
- C11–C14, installation changes, other feature branches, push and integration are
  outside this stopping boundary. Worktree/branch are preserved for continuation.
