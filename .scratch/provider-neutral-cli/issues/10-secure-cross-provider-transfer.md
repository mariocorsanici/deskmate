# 10: Protect cross-provider transfers

**What to build:** Add bounded Session delta context to a Provider switch only after local redaction, a complete preview and explicit user consent, using a private and short-lived transfer bundle.

**Blocked by:** 06: Make logs and metrics Provider-aware; 08: Extract bounded Session deltas; 09: Implement a degradable Provider switch.

**Status:** ready-for-agent

- [ ] The preview shows source and target Providers, Project card identity, bundle size, coverage, included and omitted counts, and redaction categories and counts.
- [ ] Likely secrets are redacted locally before any target Provider receives the bundle.
- [ ] Every removal is reported by category and count; redaction is never silent.
- [ ] A suspected secret that cannot be safely redacted blocks transfer and offers review, removal or replacement.
- [ ] Explicit consent is required and there is no non-interactive bypass in this release.
- [ ] The approved bundle is created privately with mode `0600`, and only its path is passed to the target Provider.
- [ ] The bundle is deleted after the target reads it, and abandoned bundles older than one hour are cleaned up safely.
- [ ] Audit events contain metadata and outcome but never bundle or finding contents.
- [ ] Synthetic canary tests prove that sensitive values do not appear in command arguments, audit records or unredacted previews.

