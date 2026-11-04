# Work session routing — ticket 07

## Intent and agreed behavior

Continue a Project predictably through the Provider and native Work session
recorded by its shared Project card. Use the Default provider when no Work
session is owned. Keep the existing Python standard-library core and adapters.

The owner approved these rules on 2026-11-04:

- A recorded, available Work session resumes with its recorded Provider.
- A recorded Work session that cannot be recovered requires an explicit choice
  before starting a replacement, even if the Default provider is available.
- A failed or cancelled launch leaves Project card ownership unchanged.
- A new Work session becomes the owner only when its real native ID is known.
- Preserve evidence of launch attempts so ticket 09 can identify potentially
  simultaneous Work sessions and request confirmation before a Provider switch.
- Postpone authenticated manual checks; this ticket must not start a real Claude
  Work session or make model requests. Use isolated synthetic automated tests.

## Approaches

The existing feature spec selects routing in the provider-neutral core, with
native launch/resume behind the adapters. Extending the Claude-only launcher
would duplicate routing rules. Asking callers to choose an adapter would leave
the ticket's automatic routing unimplemented. Keep the selected core approach.

## Implementation decisions delegated to the builder

Expose `deskmate work-session --folder PATH` for normal continuation and
`--new [--provider claude|codex]` for an explicit new Work session. Require
`--new` with `--provider` so the option cannot masquerade as cross-provider
resume. Preserve the existing low-level commands until the caller migration
and clean cut in later tickets. Support `--title`, `--prompt` and `--dry-run`.

Use a per-project launch journal and a private launch correlation ID carried
through the adapter's terminal command to its native hooks. A launch submission
is pending, not proof of a running native Work session. A matching SessionStart
or first UserPromptSubmit hook confirms the native ID. Preserve an existing
card's Markdown and use revision-checked atomic ownership writes. A missing
card can receive a minimal initial card after confirmation. Never attribute an
unrelated session merely because it uses the same folder.

Prepare, submit and confirm launch attempts under short project locks. Hooks
may arrive before terminal submission returns: record that evidence but commit
ownership only after submission succeeds. Failures, stale revisions, ambiguous
hook identity and missing native confirmation remain explicit and recoverable.
Do not hold the project lock while launching the terminal or waiting for hooks.

## Scope and validation

This ticket adds routing, truthful ownership and launch-attempt evidence. Session
delta transfer, Checks-based Provider switching, secret redaction/consent,
simultaneous-session switch confirmation and skill/reminder migration belong to
tickets 08–12. The early smoke checks and full native acceptance remain pending.

Exercise the public `bin/deskmate` boundary with isolated HOME, CODEX_HOME,
DESKMATE_DATA_DIR, synthetic native stores and fake Provider/iTerm executables.
Cover normal resume, default new sessions, explicit recovery, rejected implicit
switches, launch errors, hook timing, stale card revisions and competing attempts.
