# C14 Provider acceptance — 2026-11-14

**Provider integration acceptance passed.** Both native Default providers, both
switch directions, unavailable-source recovery and exact same-Provider resume
are now recorded. The run exposed and repaired **C14-CODEX-03**, a shared Codex
daemon retaining another launch's environment. Calendar import and launchd
scheduling remain separate unverified platform follow-ups. No push or merge.

## Source and isolation

Started from `0182bd801b0e30989ad70913064346d6e0977a0f`. All 53 implementation/test
files matched the feature worktree before testing. The owner authorized the
native continuation. The isolated fixture was
`/private/tmp/deskmate-c14-cross-20261113-em303n4n`, with non-sensitive files,
separate HOME, native configuration and data. Native clients were Claude Code
2.1.325 and Codex CLI 0.168.0; the reused managed daemon was 0.169.0. Launches used
the product's real iTerm command submission, without an environment transport
wrapper. The owner handled native hook/folder trust; the coordinator did not
select trust approvals, copy credential values or install personal integrations.

## C14-CODEX-03: shared daemon correlation

The new Codex client carried launch ID `75ad2e4d3cf845f3a4f3c87db8089286`, but
its daemon retained `e0a87223afdc405b955774bc5dc37ab8` from November 13. Native hooks
therefore confirmed the old pending attempt with session
`01a1dbcc-f515-7d40-b050-3f53993dbb27`; the actual new launch and subsequent resume
remained submitted. Its native tool environment also reported the previous
terminal identity. Transfer delivery alone did not prove correct ownership.

Deskmate now passes `--no-daemon` for new and resumed Codex sessions. This keeps
hooks attached to the selected launch environment without editing native trust,
sandbox policy, native archives or the user's daemon configuration. Two public
regressions model a pre-existing server with stale HOME, Codex home, data root and
launch ID: both failed with `pending` before the fix and pass with confirmation
and no writes to the stale root. Existing argv contracts were updated.

Local 0.167.0 help and 0.168.0 new/resume help expose the flag; native acceptance
uses 0.168.0. Tests with fake executables do not establish support for every older
Codex release. Dedicated processes trade shared-server reuse for correct launch
identity; no performance improvement is claimed.

## Native results

| Scenario | Observed result |
| --- | --- |
| Both providers, both defaults | Setup twice is idempotent for each default; shared links/hooks and reminder order verified. Two real unowned launches selected their configured provider and confirmed ownership in independent data roots. |
| Claude default | Native folder-trust dialog was displayed and later accepted through the UI; session `9736efe5-aeb9-4db1-8e74-af77a2e81e0a` matches the selected folder and launch journal. |
| Codex default | Session `01a1dbe5-2672-77a2-af3c-bfae57abdf3e` confirmed launch `e7cac352733a442ea52c7cb13652801d` in the alternate data root, while the old daemon remained available. |
| Source/history unavailable | Claude was absent from the selected PATH and its selected native archive was empty. Preview disclosed zero messages and unavailable coverage; Codex consumed the card-plus-Checks bundle, passed the live Check and confirmed launch `2f88d62dd6e74a979f98900df865849c` as session `01a1dbdd-7aa7-7bd3-86e7-96f7c578e582`. |
| Codex → Claude after repair | Native Checkpoint revision 7 and a conversation-only marker `POSTCKPT-CODEX-FIX-8R2`. Preview included three bounded messages after the Checkpoint; interactive overlap/transfer consent preceded launch. New Claude session `fa0545ca-de37-4e3d-9fd2-1ebf7174807c` confirmed launch `bc86b661b79f44db927e168d6ccd6346`, recovered the marker and passed the Check. |
| Claude → Codex after repair | New conversation-only marker `POSTCKPT-CLAUDE-FIX-6T1`; preview included four readable messages from the new Claude session, whose card did not yet contain its own Checkpoint. Codex recovered the marker, passed the Check and confirmed new session `01a1dbe6-b14c-7482-a6f6-0d0659fb5c63` under launch `d42cbd852dd64b61b4a019c6f4a0e2d9`, card revision 8 → 9. |
| Same-Provider resume | After a normal full exit and matching SessionEnd for that new Codex launch, Deskmate resumed the same native ID under fresh launch `566615b672b643e988863f53b03dcbed`. Its exact journal attempt confirmed, card revision 9 → 10, native Check passed and the conversation marker remained available. |
| Bundle lifecycle | Both healthy directions used new target identities and path-only transfer prompts, consumed the managed bundle through the public native command and left no bundle in the normal transfer directory. Current Checks were actually rerun. |

The first untrusted Codex turn consumed a transfer before hook trust was persisted;
it did not confirm ownership and was not counted as a pass. A later trusted launch
exposed the stale-daemon defect. Both observations remain in the evidence.
Source-unavailable recovery does not repair cold SQLite reads: that bounded
limitation remains documented separately, with explicit unavailable coverage.

## Verification

- Before the repair: 277/277 baseline tests passed; two new regressions then
  observed `pending` instead of `confirmed`.
- Focused repair suites: **38/38 passed**, ResourceWarnings as errors.
- Final preparation full suite: **279/279 passed**, Python 3.14.6, 131.433s.
- System Python 3.9.6 launch/adapter/routing suites: **70/70 passed**, 82.830s.
- Original feature-worktree destination: **279/279 passed**, 144.047s.
- Independent read-only review: no Critical, Important or Minor findings; it also
  passed the 14 launch-environment and 24 adapter tests and whitespace checks.

The intermediate full suite had one old argv expectation that omitted the new
flag; its expectation was corrected before the final full run. The first RED
capture ended with a shell `cat`, so its shell exit was 0; the two explicit
assertion failures in the log are the RED evidence, not a claimed shell status.
Actual commands, outputs and source hashes are in the JSON evidence.

## Platform follow-ups and cleanup

The actual morning/evening reminder scripts displayed real native macOS alerts
and recorded responses with the displayed provider and empty native session/cwd.
The test only prefixed the alert title and shortened its give-up timeout from
3600 to five seconds, setting the configured time to now. Real returned button
responses were `Ok, si parte` and `Ok, chiudo`; original configuration was restored.
No LaunchAgent was installed, and scheduling/power-off behavior is not claimed.

An attempted disposable Apple Calendar preparation returned AppleEvent error
-10000; no event import was attempted. The same error prevented confirming
whether calendar creation left an empty container. This is retained as an
unverified platform follow-up. After the owner questioned its relevance, calendar
work was separated from the Codex acceptance scope and no further Calendar action
was taken. No calendar delivery result is inferred.

Normal exit requests closed most fixture clients. A few remaining TUIs and the
daemon updater required SIGTERM, restricted to processes whose HOME exactly
matched the disposable fixture. No numeric CLI exit status is inferred. In
particular, the last resumed Codex attempt remains `ended=false` because its
forced cleanup did not produce SessionEnd; the earlier normal exit of the same
ID before resume did produce SessionEnd. No journal ending was fabricated.

The obsolete managed fixture daemon was stopped with its official command; all
remaining fixture native processes were then verified absent. The two temporary
authentication symlinks were removed without reading/copying their targets. An
unused 2492-byte bundle from the abandoned auxiliary onboarding fixture was
explicitly discarded after its process stopped. Personal native configuration
and the current `develop` worktree were not edited. C15/C16 remain unimplemented;
the feature has not been pushed or merged.

Evidence: [commands, native observations, hashes and cleanup](c14-cross-provider-2026-11-14.json).
