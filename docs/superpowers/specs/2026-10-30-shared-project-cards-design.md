# Shared Project Cards Design

## Intent

Give every project one provider-neutral Project card that preserves the latest
Checkpoint and current Checks across Claude Code and Codex CLI Work sessions.
The shared card becomes the source of truth; Claude keeps native access through
a symlink at its existing memory path.

## Goals

- Derive a stable, recognizable project identity from its canonical path.
- Keep cards readable and editable as Markdown.
- Make schema, revision and Work session ownership machine-validatable.
- Serialize writers and reject stale updates without losing the current card.
- Migrate an existing Claude card with a recoverable backup.
- Make migration idempotent and safe to resume after interruption.
- Reject unsupported future schemas before any mutation.

## Non-goals

- Provider transcript discovery, launch or resume behavior.
- Provider switching and Session delta transfer.
- Installation-wide discovery of every historical project; ticket 13 will
  orchestrate migration by calling this module for known projects.
- Structured replacements for shell Checks.
- General-purpose Markdown or YAML parsing.

## Constraints

- Python standard library only.
- All externally visible behavior is exercised through `bin/deskmate` with an
  isolated home and `DESKMATE_DATA_DIR`.
- Existing Claude Project card content must remain human-readable and must not
  be duplicated into a second writable source.
- Flexible shell Checks retain their current read-only convention and timeout.

## Approaches considered

### Whole-document compare-and-swap command — selected

Expose a small `deskmate card` interface. Callers submit a complete candidate
document with the revision they read; the module owns metadata, locking,
validation, backup and replacement. This keeps storage and concurrency logic
local while leaving Markdown composition to the skills that understand it.

### Section-specific commands

Commands such as `update-status` and `update-checks` would simplify individual
callers, but would couple the core to every Markdown section and make its
interface grow as card content evolves.

### Direct file editing plus migration helpers

This changes fewer callers initially, but lets any writer bypass revision and
locking rules. It does not meet the concurrency requirement.

## Module and seam

`tools/project_cards.py` is a deep module behind the stable command seam:

```text
deskmate card locate <project-folder>
deskmate card list
deskmate card write <project-folder> --expected-revision N
                    --provider claude|codex --session-id ID --from FILE
deskmate card migrate <project-folder>
```

- `locate` prints the canonical card path and current metadata when present.
- `list` prints every shared card path in project-key order.
- `write` creates a card when the expected revision is `0`, or atomically
  replaces it when the stored revision matches. It increments the revision and
  writes authoritative ownership metadata. It also ensures that the legacy
  Claude card path is a symlink to the shared card.
- `migrate` imports the legacy Claude card for the supplied project, creates a
  content-addressed backup, and replaces the legacy path with a symlink.

The command accepts candidate content through a file rather than process
arguments. Exit status `3` means revision conflict; stdout contains the current
card and stderr identifies its revision, so the caller can reread and compose a
new update. Other validation and migration conflicts return status `2` and do
not mutate state.

`bin/deskmate` remains responsible for the common human/JSON envelope. Storage
helpers are internal implementation, not additional caller-facing interfaces.

## Project identity and storage

Resolve the project folder to an existing canonical absolute path. Its key is:

```text
<slug>-<first 12 hex characters of SHA-256(canonical UTF-8 path)>
```

The slug is the final path segment, lowercased, with non-alphanumeric runs
replaced by `-`, trimmed, and defaulted to `project`. The hash prevents
collisions between same-named folders while the slug keeps paths recognizable.

Cards live at:

```text
<DESKMATE_DATA_DIR>/projects/<project-key>/project-card.md
```

Lock files live beside the card and remain stable across atomic replacement.

## Markdown and metadata

The card remains ordinary Markdown with frontmatter. Existing Claude fields
such as `name`, `description` and `type` are preserved. Deskmate owns one
single-line JSON field:

```markdown
---
name: project-card
description: Current durable project state
type: project
deskmate: {"provider":"claude","revision":3,"schema_version":1,"session_id":"abc"}
---
```

The JSON object must contain exactly:

- `schema_version`: integer `1`;
- `revision`: positive integer;
- `provider`: `"claude"`, `"codex"` or `null`;
- `session_id`: non-empty string or `null`.

Provider and session are either both set or both `null`. Unknown fields,
duplicate `deskmate` lines, invalid JSON, invalid values and future schemas are
rejected. Candidate metadata is never trusted: `write` replaces it with values
derived from the stored revision and command arguments.

A legacy document without frontmatter receives a minimal frontmatter block;
its original bytes become the Markdown body unchanged.

## Concurrency and writes

Each operation that may mutate a card takes an exclusive `fcntl.flock` on the
project's stable lock file. Under the lock, `write` rereads and validates the
current card, compares its revision with `--expected-revision`, and only then
builds the replacement.

The replacement is written to a same-directory private temporary file, flushed,
then installed with `os.replace`. A stale writer receives the current card and
revision instead of overwriting it. Revision `0` is valid only when no shared
card exists.

Before a first `write`, the module inspects the legacy Claude card path. A
missing path or a symlink already targeting the shared card is safe. A regular
legacy card requires `migrate`; `write` refuses to create a parallel shared
card. After a successful create or update, the module idempotently ensures the
Claude symlink. If link creation is interrupted after the shared write, the
next `locate`, `write` or `migrate` repairs it.

Read-only operations validate metadata but do not need to retain the lock after
the complete file has been read, because replacement is atomic.

The concurrency guarantee covers Provider and automation writers using
`deskmate card write`. Markdown remains directly inspectable and manually
editable for recovery, but an editor writing through the symlink does not
participate in locking or revision checks; concurrent manual editing is outside
the supported update protocol and is documented as such.

## Claude migration

For the supplied project folder, compute the legacy Claude path using the
existing non-alphanumeric-to-hyphen folder-key rule:

```text
~/.claude/projects/<legacy-key>/memory/project-card.md
```

Migration runs under the shared project lock:

1. Validate any existing shared card before mutation.
2. If the legacy path is already a symlink to the shared card, report an
   idempotent success.
3. Read the legacy regular file and create a byte-for-byte backup at
   `<data>/backups/project-cards/<project-key>/<sha256-of-content>.md` using
   exclusive creation. The content hash makes repetition reuse the same backup.
4. If no shared card exists, add revision `1` metadata and atomically create
   the shared card from the legacy content. If the latest Checkpoint line names
   a session ID, record ownership as Claude plus that session; otherwise both
   ownership fields are `null`.
5. If a shared card already exists, compare the legacy content with the shared
   document after removing Deskmate metadata. Equal content can continue;
   differing content is a migration conflict and both copies remain untouched.
6. Atomically replace the legacy regular file with a symlink to the shared
   card.

The backup is created before either source is replaced. Repeating any completed
or partially completed migration does not create duplicate backups or discard
content. An unsupported shared schema stops before backup or symlink changes.

## Existing callers

- `tools/check.py` discovers shared cards under the Deskmate data directory;
  explicit card paths continue to work.
- `/checkpoint` locates and writes cards through `deskmate card`, including the
  revision it read and current Provider/session ownership. It continues to add
  the native Claude `MEMORY.md` pointer when needed; that pointer is discovery
  configuration, not Project card state.
- `/call-it-a-day` and `/whats-on-today` discover shared cards instead of
  globbing Claude memory paths.
- The legacy Claude symlink lets Claude native memory discovery continue to see
  the same bytes without creating another source of truth.

Only callers necessary to establish the shared source of truth change in this
ticket. Provider-specific adapter behavior remains in tickets 04 and 05.

## Errors and recovery

- Missing project folder: usage/configuration error, no storage created.
- Missing legacy card during migration: successful no-op with an explicit
  report; later writes can create the shared card.
- Invalid or unsupported metadata: status `2`, no mutation.
- Revision mismatch: status `3`, current card returned for retry.
- Backup, temporary write or symlink failure: nonzero status; pre-existing card
  content remains recoverable.
- Legacy/shared content conflict: status `2`, both regular files and the backup
  remain available for explicit resolution.

## Testing

Command-level tests cover:

- canonical equivalent paths, readable slug and same-name collision resistance;
- creation, read/location, listing and deterministic metadata;
- valid updates, stale writers and current-content conflict output;
- invalid metadata, ownership pairs and future schema rejection;
- atomic replacement behavior and lock serialization;
- migration backup, symlink compatibility, repetition and partial-resume states;
- differing legacy/shared content without loss;
- shared-card discovery by Checks;
- isolated home and data directories with no access to real user state.
