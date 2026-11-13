# Provider launch environment

User approved proceeding with the targeted launch-environment fix on 2026-11-13 after discussing its behavior and tradeoffs. Execute inline, with a final fresh-context review. Cross-Provider model requests remain held; Claude-only native verification is authorized.

## Intent

A Provider launched by Deskmate must use the same executable, HOME, PATH and native configuration roots used for discovery and routing. It must not silently switch to iTerm profile defaults. Fix both Claude and Codex while retaining native ownership confirmation and ordinary permissions.

## Approach and tradeoffs

Selected: resolve the native executable to an absolute lexical path, capture only HOME/PATH/ZDOTDIR/Claude configuration/Codex home/Deskmate data and launch identity, and submit an explicit command to iTerm's default profile. Start the existing macOS zsh shell under the selected HOME/ZDOTDIR, retain normal login/interactive startup for user-provided tool settings, then reapply selected paths and exec the chosen CLI. The iTerm profile appearance and exit policy still apply; its unrelated shell is not started first. Preserve symlink/shim executable names. Normalize relative path entries against the invocation directory.

Alternatives: copying every environment variable carries unnecessary application state; relying on a test wrapper leaves production broken. Both are rejected. Normal use retains the caller's selected environment; custom homes may require their own native authentication. Do not copy credentials, inject bypass permissions or change personal integration.

Honor CLAUDE_CONFIG_DIR consistently in native storage, hooks, installation, legacy card links and usage readers when explicitly selected. When absent, keep it absent in the launched CLI (its presence can affect native authentication behavior), and use HOME/.claude internally. Pin the effective CODEX_HOME including its default. Keep unrelated environment inherited by iTerm rather than serializing it; explicitly override/unset only the selected native keys and stale launch identity.

## Boundaries

Python standard library, Python 3.9 compatibility, macOS/iTerm. No data migration, dependency installation, push or merge. Do not implement ticket 15's process-start confirmation or ticket 16 reminders in this change. Submitting through the iTerm command API avoids line typing, but does not itself establish native startup; existing hooks retain that confirmation role.

## Acceptance

Public launch/routing tests must execute the transported command under a different simulated profile HOME/PATH/config and prove the selected CLI, same config/data, canonical cwd and hook identity. Cover both providers, explicit/default config, relative and quoted paths, new/resume, absent versus set CLAUDE_CONFIG_DIR, and failure before submission. Full suite, system-Python relevant suites and independent review pass. Claude native resume through the product must succeed without the osascript environment wrapper; record authentication workaround separately and clean it up. C14 remains open while cross-Provider and other platform observations remain pending.
