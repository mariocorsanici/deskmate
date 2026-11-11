# Checkpoint timestamp validation

Approved scope: the owner accepted system-generated ISO timestamps, shared validation before publication, regression coverage and a native Checkpoint/retrospective rerun.

The checkpoint skill obtains a UTC ISO 8601 timestamp with seconds from Python. A small `tools/checkpoints.py` module owns timestamp and Checkpoint-line parsing. `card write` validates an existing Status Checkpoint before creating storage; `session-delta` uses the same parser after verifying card ownership. Cards without a Checkpoint remain valid. Existing accepted ISO offsets and legacy local minute timestamps retain their meaning; malformed existing cards still produce the documented bounded fallback and warning. Invalid new candidates return exit 2 without publishing or incrementing revision.

Approaches considered: prose guidance alone leaves invalid publication possible; accepting timezone abbreviations expands ambiguity; system-generated timestamps plus shared validation closes the observed gap at publication. The owner approved the latter. No schema change, new CLI command, migration, native Claude request, push or merge.
