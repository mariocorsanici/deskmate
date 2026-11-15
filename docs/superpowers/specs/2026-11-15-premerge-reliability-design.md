# Provider reliability required before integration

The owner requires four outstanding items resolved before merging
`feature/codex-cli-support`: C15 startup verification, C16 morning reminders after
power-off, readable persisted Codex history after native exit, and normal native
session closure with observed lifecycle finalization. Calendar is excluded.
Autonomous implementation and isolated native validation remain authorized.

## Decisions

- Keep one shared command/core and both native adapters. Shared iTerm transport
  owns private launch payloads and a bounded, tty-specific process check; native
  hooks alone confirm the provider-native identity and Project card ownership.
- Carry initial prompts in private disposable files, never typed terminal lines
  or a large AppleScript command. Preserve shell/environment selection and Codex
  `--no-daemon`; support new and resumed sessions equally. A failed start returns
  an actionable error identifying the tab/tty and keeps inspection possible.
- Trigger morning reminders at login and at the configured time, within the
  configured working-day window. Serialize concurrent invocations; record the
  once-per-local-date display at display time, without waiting for a response.
  Preserve evening behavior. Existing LaunchAgents are reloaded transactionally.
- Keep all native Codex files read-only. Prefer the ordinary live SQLite reader.
  A fallback must recover complete cold data without ignoring committed WAL:
  use a verified stable private snapshot when native WAL sidecars are absent,
  with mutation/race refusal and complete private-file cleanup. Never repair the
  native database by opening it read-write or using a general immutable reader.
- Reproduce native closing independently of the previous UI automation. The
  earlier `/exitexit` input is not product evidence. Correct the harness and
  require real SessionEnd plus an ended journal for normal new/resume exits.
  Any additional production finalization must represent its evidence truthfully;
  never manufacture a native event or close another still-running session.

## Alternatives and boundaries

Initializing native SQLite WAL with a writable connection is rejected because it
mutates provider-owned storage. Reading a live native database as immutable is
rejected because it may omit committed WAL. A cold private copy is acceptable
only with evidence that no native writer raced the copy. A full persistent cache
of conversations is unnecessary and would retain sensitive data.

Do not infer process start from successful AppleScript submission, infer native
identity from a filename or pid, suppress normal native trust/permission prompts,
or treat degraded history as a completed cold-read repair. A hard-killed runtime
cannot be claimed to have emitted a native end hook.

Use existing Python 3.9+ standard-library and macOS/zsh conventions. Use disposable
homes/data/native configurations, no personal integration install, no calendar
actions, no push or merge. Confirm each change with a failing regression before
implementation, complete suite verification and final independent review.
