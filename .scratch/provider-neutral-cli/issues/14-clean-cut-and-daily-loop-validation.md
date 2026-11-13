# 14: Perform the clean cut and validate the Daily loop

**What to build:** Finish the migration to the provider-neutral architecture, remove replaced Claude-only entry points, document the final user experience and prove the complete Daily loop with both Providers.

**Blocked by:** 07: Route Work session launch and resume; 10: Protect cross-provider transfers; 11: Make the retrospective progressive; 13: Complete installation, migration and removal.

**Status:** ready-for-agent

**Implementation:** synthetic implementation verified; Codex native execution recorded; C14-CODEX-02 triaged as a documented bounded runtime limitation; Claude-only execution recorded; C14-CLAUDE-01 eligibility/discovery repair verified (263 full tests, 76 compatibility checks); remaining native launch and cross-Provider acceptance pending.
**Owner:** `/root`, started 2026-11-10 from `b10d282`.

- [x] Every skill, hook, reminder and documented command uses the provider-neutral interface.
- [x] Replaced Claude-only entry points are removed rather than retained as a deprecation layer.
- [x] Repository-wide reference checks find no stale calls to removed entry points.
- [x] Documentation explains setup, native skill syntax, Default provider behavior, resume and Provider switch behavior.
- [x] Automated tests cover the complete Daily loop with Claude only, Codex only and both Providers installed.
- [x] A manual acceptance run uses dedicated non-sensitive Claude and Codex Work sessions.
- [ ] Manual acceptance verifies skill discovery, hook logging, same-Provider resume and a real Provider switch in both directions.
- [x] Temporary tracker decisions are either promoted to durable documentation or identified for removal before merge.

## Comments

C14 independent implementation follows Task 6 of the existing core-completion plan. See `docs/testing/daily-loop.md` for the final command contract, automated/instruction scenarios, explicit native matrix and tracker disposition. Native checkboxes remain open; no personal installation, native request, push or merge.

Synthetic validation: 248/248 full-suite tests on Python 3.14.6; 27/27 Daily-loop and transfer scenarios on Python 3.9.6; ResourceWarnings as errors. One independent whole-feature review; both Important findings fixed with RED/GREEN regressions. No new review findings deferred. Destination full suite passed before the local checkpoint commit; see Git history for its identity.


2026-11-11: Codex native Daily loop executed. C14-CODEX-01 fixed with shared timestamp validation and system-generated UTC skill output; 253/253 full tests, 47/47 card/delta tests on both Python versions, one independent review without findings, and a fresh native Checkpoint/selected-retrospective regression passed. See `docs/testing/c14-codex-timestamp-fix-2026-11-11.md`. Separate C14-CODEX-02 records cold read-only SQLite history access after CLI exit; it is not fixed here. Claude/cross-Provider groups remain on hold and C14 stays open.

2026-11-13: C14-CODEX-02 triaged with cold metadata/history reproductions inside and outside the sandbox. Keep strict read-only access and explicit degraded/unavailable coverage; no production reader change or unconditional cold-history reliability claim. Public-command regressions cover nonmutation, fixture-modeled lifecycle recovery and fresh live WAL. Full suite 255/255; adapter/delta suites 51/51 on system Python; reviewed evidence in `docs/testing/c14-codex-sqlite-2026-11-13.md` and JSON. Claude-only native acceptance authorized and launched separately on isolated source 8ab2f78; results pending. Cross-Provider requests remain held. C14 stays open; no push or merge.

2026-11-13: Owner requested committing Codex work and resuming C14. Codex cold-WAL tests/docs committed as `3fe01e7`, preserving the independent ticket-spec commit `67cc376`. Claude-only native evidence is now preserved on this branch. C14-CLAUDE-01 reproduces as public resume dry-run exit 4 for the actual native fixture; repair uses recorded native SessionStart identity plus a unique transcript without opening conversation files. Original native fixture dry-run now exits 0. Automated regression/compatibility/review results follow in `docs/testing/c14-claude-resume-fix-2026-11-13.md`. Actual repaired terminal submission, manual permission dialogs and cross-Provider acceptance remain unverified; C14 stays open.

Repair verification: preparation full suite 263/263 (107.043s); system-Python routing/adapter/delta 76/76 (65.110s); independent review approved without findings. Actual native fixture public routing/discovery succeeds and data hashes are unchanged. This validates repaired eligibility, not an actual repaired iTerm launch.

Destination verification of C14-CLAUDE-01 repair: 263/263 full tests passed in 109.403s before the local commit. Actual repaired terminal submission is being checked separately; cross-Provider requests remain held.
