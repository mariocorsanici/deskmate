# 14: Perform the clean cut and validate the Daily loop

**What to build:** Finish the migration to the provider-neutral architecture, remove replaced Claude-only entry points, document the final user experience and prove the complete Daily loop with both Providers.

**Blocked by:** 07: Route Work session launch and resume; 10: Protect cross-provider transfers; 11: Make the retrospective progressive; 13: Complete installation, migration and removal.

**Status:** ready-for-agent

**Implementation:** Provider acceptance completed on 2026-11-14: both native defaults, both real switch directions, source/history-unavailable recovery, correct native launch ownership and same-ID resume. C14-CODEX-03 repaired with dedicated Codex processes; 279/279 full tests and 70/70 compatibility checks. Calendar import/launchd remain separate platform follow-ups, not claimed as verified.
**Owner:** `/root`, started 2026-11-10 from `b10d282`.

- [x] Every skill, hook, reminder and documented command uses the provider-neutral interface.
- [x] Replaced Claude-only entry points are removed rather than retained as a deprecation layer.
- [x] Repository-wide reference checks find no stale calls to removed entry points.
- [x] Documentation explains setup, native skill syntax, Default provider behavior, resume and Provider switch behavior.
- [x] Automated tests cover the complete Daily loop with Claude only, Codex only and both Providers installed.
- [x] A manual acceptance run uses dedicated non-sensitive Claude and Codex Work sessions.
- [x] Manual acceptance verifies skill discovery, hook logging, same-Provider resume and a real Provider switch in both directions.
- [x] Temporary tracker decisions are either promoted to durable documentation or identified for removal before merge.

## Comments

C14 independent implementation follows Task 6 of the existing core-completion plan. See `docs/testing/daily-loop.md` for the final command contract, automated/instruction scenarios, explicit native matrix and tracker disposition. Native checkboxes remain open; no personal installation, native request, push or merge.

Synthetic validation: 248/248 full-suite tests on Python 3.14.6; 27/27 Daily-loop and transfer scenarios on Python 3.9.6; ResourceWarnings as errors. One independent whole-feature review; both Important findings fixed with RED/GREEN regressions. No new review findings deferred. Destination full suite passed before the local checkpoint commit; see Git history for its identity.


2026-11-11: Codex native Daily loop executed. C14-CODEX-01 fixed with shared timestamp validation and system-generated UTC skill output; 253/253 full tests, 47/47 card/delta tests on both Python versions, one independent review without findings, and a fresh native Checkpoint/selected-retrospective regression passed. See `docs/testing/c14-codex-timestamp-fix-2026-11-11.md`. Separate C14-CODEX-02 records cold read-only SQLite history access after CLI exit; it is not fixed here. Claude/cross-Provider groups remain on hold and C14 stays open.

2026-11-13: C14-CODEX-02 triaged with cold metadata/history reproductions inside and outside the sandbox. Keep strict read-only access and explicit degraded/unavailable coverage; no production reader change or unconditional cold-history reliability claim. Public-command regressions cover nonmutation, fixture-modeled lifecycle recovery and fresh live WAL. Full suite 255/255; adapter/delta suites 51/51 on system Python; reviewed evidence in `docs/testing/c14-codex-sqlite-2026-11-13.md` and JSON. Claude-only native acceptance authorized and launched separately on isolated source 8ab2f78; results pending. Cross-Provider requests remain held. C14 stays open; no push or merge.

2026-11-13: Owner requested committing Codex work and resuming C14. Codex cold-WAL tests/docs committed as `3fe01e7`, preserving the independent ticket-spec commit `67cc376`. Claude-only native evidence is now preserved on this branch. C14-CLAUDE-01 reproduces as public resume dry-run exit 4 for the actual native fixture; repair uses recorded native SessionStart identity plus a unique transcript without opening conversation files. Original native fixture dry-run now exits 0. Automated regression/compatibility/review results follow in `docs/testing/c14-claude-resume-fix-2026-11-13.md`. Actual repaired terminal submission, manual permission dialogs and cross-Provider acceptance remain unverified; C14 stays open.

Repair verification: preparation full suite 263/263 (107.043s); system-Python routing/adapter/delta 76/76 (65.110s); independent review approved without findings. Actual native fixture public routing/discovery succeeds and data hashes are unchanged. This validates repaired eligibility, not an actual repaired iTerm launch.

Destination verification of C14-CLAUDE-01 repair: 263/263 full tests passed in 109.403s before the local commit. Actual repaired terminal submission is being checked separately; cross-Provider requests remain held.

Authenticated native follow-up after repair: Deskmate submitted a real iTerm launch and resumed the original Claude session; matching SessionStart confirmed the journal, read-only Check passed, exit 0 and SessionEnd ended the attempt. Owner/body unchanged; revision 2->3 is ownership confirmation. Manual-mode prompt observed; coordinator approval keystroke was denied and human approval inferred from execution. Test transport explicitly supplied isolated HOME/PATH; temporary auth link removed. See `docs/testing/c14-claude-native-resume-2026-11-13.md`. C14 remains open for cross-Provider/remaining observations; no push or merge.

2026-11-13: Owner authorized correcting selected HOME/PATH/native-config propagation after the wrapper-based follow-up exposed C14-ENV-01. Shared environment selection and direct iTerm command submission are under verification on both adapters; custom Claude config consumers are aligned, ordinary selected zsh startup retained, and selected paths reapplied before native execution. Four initial public regressions observed RED, then GREEN; no real Codex/cross-Provider requests authorized. Actual Claude verification without an environment wrapper follows. See `docs/testing/c14-launch-environment-2026-11-13.md`.

C14-ENV-01 automated verification: 277/277 preparation tests, 118/118 relevant system-Python tests, independent review approved and three actual AppleScript programs compiled outside the sandbox. Original-worktree full suite passed 277/277 in 124.183s before local repair commit. Native Claude proof without wrapper is recorded separately; cross-Provider requests remain held.

C14-ENV-01 native acceptance completed: actual Deskmate/iTerm Claude resume used /usr/bin/osascript with no wrapper or in-tab exports. Process/native command confirmed selected HOME/PATH/ZDOTDIR/native roots and absent CLAUDE_CONFIG_DIR; Check exit 0 after the user approved the ordinary manual prompt. Start/end hooks and confirmed/ended journal match the original ID/cwd; owner/body preserved, revision 3->4 expected. CLI process exited; its numeric exit code was not observable. Temporary auth link removed, implementation hashes unchanged. Native evidence: `docs/testing/c14-launch-environment-native-2026-11-13.md`. Codex transport is automated coverage only in this repair; cross-Provider native requests remain held.


2026-11-14: Owner requested autonomous C14 execution. Reused the isolated 0182bd8 fixture after checking all 53 implementation/test files against the feature worktree. Native Codex exposed C14-CODEX-03: a reused daemon retained an old DESKMATE_LAUNCH_ID and confirmed the wrong pending journal attempt. Two public regressions observed RED; new/resume now use --no-daemon, preserving ordinary trust/sandbox/storage. Both native defaults, healthy switches in both directions, zero-message unavailable-source recovery and exact-attempt same-ID Codex resume passed after repair. Normal native approvals were left to the owner. Full preparation suite 279/279, system-Python 70/70 and independent review passed; destination verification is recorded in the native report. C15/C16 were not implemented. Calendar was separated from the Codex acceptance scope after the owner's clarification; no import claimed. No push or merge. Retain this tracker until integration.
