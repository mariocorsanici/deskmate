# C14 launch environment — 2026-11-13

Base: `f22022e`. The owner authorized the targeted launch-environment fix after
reviewing its scope and tradeoffs. Both adapters are covered with fake native
CLIs; Claude-only native follow-up is authorized. Cross-Provider native requests
remain held. This work does not close C14 or implement tickets 15/16.

## Reproduction and correction

Four public regressions first failed against the unchanged source: Claude
selected the profile's different CLI (no matching hook confirmation); Codex's
absolute binary still received the profile HOME; custom-Claude resume could not
find native metadata in the selected config. Both new/resume paths were covered.

`provider_environment.py` now selects lexical absolute CLI paths, HOME, normalized
PATH/ZDOTDIR, native config roots and Deskmate data. It pins them before starting
zsh and reapplies them after startup. A fifth RED/GREEN check preserves startup
settings while preventing startup scripts from overriding verified paths.
CLAUDE_CONFIG_DIR is passed only when selected; otherwise profile configuration
is cleared for the child. Codex's effective home is explicit even at its default.
Stale launch IDs and nested-Claude sentinels from the terminal app are cleared.

The adapters use iTerm's direct command API instead of typing into a profile
shell. Window creation also uses that command, so an empty iTerm instance does
not first initialize an unrelated profile shell. Profile appearance and process
exit policy remain in force. An absolute selected shim/symlink retains its name.

Claude config selection is shared by storage, hooks, skills, installation,
legacy card links, usage and the historical session-stats diagnostic. Setup's
staged/synthetic environment remains isolated, and installed reminder agents
retain explicitly selected native config roots. No data migration is performed.

## Verification

Public tests simulate conflicting iTerm profile HOME/PATH/native config and
actually execute fake native CLIs. They verify hook-confirmed ownership, correct
native argv/cwd/environment, custom/default/absent config, relative paths, quoted
paths, symlinks, missing CLI/config errors, retained startup settings and stale
correlation clearing. Custom install/Stop usage/remove tests preserve the default
configuration and calculate counters from the selected custom transcript.

Preparation full suite: **277/277 passed** (121.231s). System-Python relevant
suites: **118/118 passed** (122.666s). Both treat ResourceWarnings as errors.
All three actual AppleScript programs compile outside the sandbox; the sandbox
could not load the iTerm dictionary. Independent review approved without findings
and independently passed the 12 fake-native launch tests.
Commands and code hashes are in the [JSON evidence](c14-launch-environment-2026-11-13.json).
Native verification must use the real osascript directly, with no environment
transport wrapper. Authentication workarounds, if needed, are recorded separately.

## Limits

Other environment is inherited from the terminal app and initialized by selected
zsh startup, not cloned wholesale from the caller. This is a selected-path
consistency guarantee, not a fully sterile or reproducible process environment.
Selected paths deliberately override profile/project startup changes. A custom
HOME/config may require its own native authentication. This targets macOS/zsh;
other shell initialization modes are outside the current platform contract.

Direct API submission avoids terminal line typing but does not add ticket 15's
bounded native-process startup check. Existing native hooks remain the ownership
confirmation. Desktop/calendar delivery and cross-Provider acceptance remain
separate pending observations. No personal integration, push or merge is changed.

Original feature-worktree verification before commit: **277/277 passed** in 124.183 seconds, ResourceWarnings as errors. Native verification without a wrapper follows separately.
