# Provider Launch Environment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Launch Claude and Codex with the same selected native environment used by Deskmate.
**Architecture:** One shared native environment/path helper feeds both adapters and native config consumers. iTerm receives a direct command, not a line typed into its profile shell. The selected HOME/ZDOTDIR initialize zsh; selected native paths are reapplied after startup.
**Tech Stack:** Python standard library, unittest, iTerm AppleScript.
**Spec:** docs/superpowers/specs/2026-11-13-provider-launch-environment-design.md

## Global Constraints

Python standard library, Python 3.9 compatibility, macOS/iTerm. No credential copying, bypass permissions, personal integration changes, push or merge. Preserve explicit native ownership confirmation. Cross-Provider native requests remain held.

## Review Focus

- Absent CLAUDE_CONFIG_DIR must remain absent, despite conflicting profile configuration.
- Relative PATH/config roots must not change meaning after chdir.
- Native executable symlinks/shims must retain their selected lexical path.
- Custom Claude configuration must be honored consistently by setup, storage and usage, including isolated staging.
- Direct terminal API submission must not be confused with verified native process startup.

### Task 1: Align environment selection and Provider launch

**Files:** Create tools/provider_environment.py; modify tools/adapter_claude.py, tools/adapter_codex.py, tools/project_cards.py, tools/token_usage.py, tools/installation.py, tools/adapter_cli.py; test tests/test_work_sessions.py, tests/test_claude_adapter.py, tests/test_codex_adapter.py, tests/test_installation.py.
**Interfaces:** Consumes existing Provider launch contract. Produces claude_home(), codex_home(), executable(name), launch_command(argv, folder, root, launch_id=None, extra=None); no new public command.

- [x] Write public regressions that simulate a different profile environment and custom native configuration; assert real fake-CLI output and hook-confirmed ownership.
- [x] Run new tests and observe selected HOME/config or binary mismatch before implementation.
- [x] Implement shared path/environment selection, consistent native config consumers and explicit iTerm command submission; preserve missing-CLI errors and focusing logic.
- [x] Run focused, full and system-Python suites with ResourceWarnings as errors; review the whole change with a fresh reviewer and resolve material findings.
- [x] Apply to original feature worktree, verify and commit the focused repair with design/plan/evidence.

### Task 2: Native acceptance without environment transport wrapper

**Files:** docs/testing/c14-launch-environment-2026-11-13.md/json; existing Daily-loop and C14 tracking docs.
**Interfaces:** Consumes Task 1 implementation; produces actual native launch evidence and remaining acceptance state.

- [x] Repoint only the existing isolated Claude fixture to the corrected source using remove/setup if needed.
- [x] Run actual Deskmate native resume with no PATH-local osascript wrapper, verify native environment/identity/folder/hooks and read-only Check, then full exit and authentication-reference cleanup.
- [x] Record first failures/workarounds, native outputs and limits. Do not claim Codex/cross-Provider model acceptance from fake-CLI tests.
- [x] Update C14 evidence/tracker and commit verified acceptance evidence.

## Recorded completion

Repair commit: `31f3cc6`. Full suite 277/277 in preparation and destination;
system-Python relevant suites 118/118; independent review approved; all three
AppleScript programs compiled. Claude real resume without environment transport
wrapper passed, with selected process/native environment, Check exit 0, matching
hooks/journal and auth-reference cleanup. Numeric native CLI exit status was not
observable. Raw evidence is in `docs/testing/c14-launch-environment-native-2026-11-13.md`
and JSON. C14 remains open; no native Codex/cross-Provider request was made.
