# Common installation and removal verification

C13 on `feature/codex-cli-support`, starting from `e375535`.

## Installed behavior

`deskmate setup` (also `./install.sh`) detects compatible Providers, supports
repeated explicit `--provider` selections, requires an explicit default for a
non-interactive dual installation, and removes owned integrations for deselected
Providers. Codex capability includes enabled native hooks. Provider output names
excluded integrations and the reason. No model request is needed for setup.

One `skills/` source, including setup, is linked under each Provider's native
skill directory. The repository-local Claude setup entry points to the same
source. `~/.local/bin/deskmate` links to the stable command; zsh/bash receive a
marked PATH block if necessary. Unrelated configuration, hook groups, skill
locations and command links are retained; collisions stop publication.

Setup preflights every configuration, shared/legacy card and log schema before
creating storage. It resolves legacy project identity from explicit `--project`
paths, card folder paths or Claude session indexes, and validates that the path
matches the native storage key. It does not decode a lossy path key or read
conversation transcripts. Unknown/moved folders require an explicit correction.
Legacy history is retained with Claude attribution and unknown CSV columns.

Provider integration is first built in disposable state. An installation plan
contains the original and proposed bytes, modes and link targets. Originals are
stored as private blobs under `<data>/backups/install/<id>/`, with a versioned
journal naming the corresponding files. Each file/link is replaced atomically
on its destination filesystem. Setup coordinates with card, log and adapter
locks and checks for intervening edits. This is recoverable multi-file
publication, not a claim that all files change in one filesystem operation.

Failures restore prior file/link state. The journal also records previous
LaunchAgent activation; recovery restores services as well as files. Rerunning
setup or removal recovers a pending journal. A changed file or corrupt backup
stops recovery with its location, retaining backups for deliberate reconciliation.
No concurrent edit is silently overwritten. Successful journals retain backups.

The published prompt hooks are executed with a synthetic native payload and a
disposable HOME/data directory; verification requires a matching Provider,
native session ID and checkpoint event. No verification row is added to the
personal log. Setup reports trust/approval guidance separately: synthetic
verification cannot prove native runtime delivery or consent. Desktop agents
retain the selected data root, and changed calendar files need importing.

Removal works without installed Provider executables, removes owned integrations
and the managed shell PATH block, and retains data, legacy-to-shared card links
and calendar files by default. Interactive purge separately defaults to no and
requires exactly `DELETE`; non-interactive purge requires `--purge-data`. Purge
also removes native card links into the deleted data. Tests never purge real data.

## Automated evidence

Baseline: 193 tests passed on Python 3.14.6 before changes. Public installation
scenarios first failed on the missing common setup/remove commands. Additional
RED/GREEN regressions cover deselecting a previously installed Provider,
byte/mode preservation on repeated setup, and native service recovery after a
forced process interruption. Native APIs are faked at the launchctl boundary;
all file, card, hook, log, shell and migration operations are real in temporary
homes. The installed command is also invoked directly to verify native-event
Provider and session identity.

A setup skill application scenario failed against the former Claude-only skill
(location restriction, Claude-only verification and writes to personal logs).
The shared replacement passed the same Codex-only/custom-data scenario, retaining
the native quota hold and default data-preserving removal. These were instruction
application checks, separate from executable test evidence.

Independent review identified six Important issues. Each received a regression
that failed on the reported behavior before the fix:

- Custom Codex home capabilities are retained from real detection while staging
  hooks; an empty synthetic home no longer overrides the effective result.
- Service-only activation now creates a journal even without changed files.
- Failed native restoration is verified and leaves the journal pending for retry.
- Configuration uses the same pre-read snapshot for validation and publication;
  a concurrent preference edit is retained and stops setup.
- Data roots are normalized consistently, including `~`, so unsupported schemas
  cannot be bypassed and preferences are not silently replaced.
- Purge refuses repository ancestors and roots containing native integrations.

A full-suite error also caught the new setup skill's missing Codex invocation
metadata; the existing adapter contract failed before adding the standard
`allow_implicit_invocation: false` file and passed afterward.

One Minor finding is deferred: the detection summary precedes `--provider`
filtering and can call an available Provider “included” even when the explicit
selection excludes it. The configuration, installed integrations and per-Provider
verification results reflect the requested selection. Read those when confirming
an override; wording can be clarified separately.

Final executable verification (2026-11-09):

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -Werror::ResourceWarning -m unittest discover -s tests -q
# Python 3.14.6: 224 tests, OK

PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -Werror::ResourceWarning -m unittest tests.test_installation -q
# Python 3.9.6: 31 tests, OK
```

The focused Python 3.14.6 installation run also passed all 31 tests.
During the destination-worktree verification, the pre-existing
`test_bounded_native_delta_is_redacted_before_preview_and_transfer` failed once:
its PTY reader reached closure after “Switch confirmed” while the parent process
had not yet been reaped, and the helper immediately reported nontermination.
The same test passed in isolation (1/1). No transfer implementation was changed;
the complete destination suite was rerun before the ticket commit. `zsh -n install.sh` and `git diff --check` passed.

## Native acceptance still pending

Actual runtime skill discovery, hook trust and authenticated delivery, desktop
alerts and calendar application import remain manual acceptance work. The
previous owner hold on native model requests remains in force. No personal
installation, calendar import, native request, push or merge is part of C13.
