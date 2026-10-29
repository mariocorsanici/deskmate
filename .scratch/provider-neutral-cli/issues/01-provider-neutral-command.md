# 01: Introduce the provider-neutral command

**What to build:** Give the user one stable `deskmate` command for the existing Claude-backed Daily loop, with human-readable and machine-readable output, while preserving current behavior. Establish an isolated command-level test seam that later Provider slices can reuse.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

**Implementation:** complete

- [x] The command exposes the current Deskmate operations without requiring callers to know the underlying scripts.
- [x] Human-readable output remains concise and useful in a terminal.
- [x] A JSON output mode has a stable envelope, deterministic fields and meaningful exit statuses.
- [x] Existing Claude Daily loop behavior remains available through the new command.
- [x] Command tests run with isolated temporary state and do not read or mutate the user's real Deskmate data.
- [x] The runtime uses only the Python standard library.

## Comments

Implemented with command-level tests for every delegated operation. Review fixes added a private data-root override for isolated state, safe top-level and per-command help, JSON help and failure envelopes, and streaming output in human mode.

