# 10: Protect cross-provider transfers

**What to build:** Add bounded Session delta context to a Provider switch only after local redaction, a complete preview and explicit user consent, using a private and short-lived transfer bundle.

**Blocked by:** 06: Make logs and metrics Provider-aware; 08: Extract bounded Session deltas; 09: Implement a degradable Provider switch.

**Status:** ready-for-agent

**Implementation:** complete (automated/public PTY acceptance; native acceptance remains C14).

- [x] The preview shows source and target Providers, Project card identity, bundle size, coverage, included and omitted counts, and redaction categories and counts.
- [x] Likely secrets are redacted locally before any target Provider receives the bundle.
- [x] Every removal is reported by category and count; redaction is never silent.
- [x] A suspected secret that cannot be safely redacted blocks transfer and offers review, removal or replacement.
- [x] Explicit consent is required and there is no non-interactive bypass in this release.
- [x] The approved bundle is created privately with mode `0600`, and only its path is passed to the target Provider.
- [x] The bundle is deleted after the target reads it, and abandoned bundles older than one hour are cleaned up safely.
- [x] Audit events contain metadata and outcome but never bundle or finding contents.
- [x] Synthetic canary tests prove that sensitive values do not appear in command arguments, audit records or unredacted previews.


## Comments

2026-11-09: Implemented protected bounded Session delta transfer with local redaction, exact byte/coverage/count manifest, uncertain-finding refusal, explicit interactive consent and no unattended bypass. The target receives only a private bundle path; `transfer-read` validates target/ownership/mode/expiry and consumes the file once. Successful later normal commands clean valid managed bundles older than one hour; previews, dry runs and delta inspection remain immutable. Audit contains Provider/card/count/category/outcome metadata only. Both switch directions and fake native ownership confirmation are exercised.

Final suite: 180/180 tests pass, no skips, ResourceWarnings as errors. All 23 switch/transfer tests also pass on macOS system Python. One independent review's four Important findings were reproduced RED and fixed GREEN. A generic transcript warning remains a deferred Minor; actual manifest coverage is accurate. See `docs/testing/provider-switches.md` for evidence and scope decisions. The owner requested stopping at this ticket's next commit; C11–C14 have not started.
