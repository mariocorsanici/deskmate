# 14: Perform the clean cut and validate the Daily loop

**What to build:** Finish the migration to the provider-neutral architecture, remove replaced Claude-only entry points, document the final user experience and prove the complete Daily loop with both Providers.

**Blocked by:** 07: Route Work session launch and resume; 10: Protect cross-provider transfers; 11: Make the retrospective progressive; 13: Complete installation, migration and removal.

**Status:** ready-for-agent

- [ ] Every skill, hook, reminder and documented command uses the provider-neutral interface.
- [ ] Replaced Claude-only entry points are removed rather than retained as a deprecation layer.
- [ ] Repository-wide reference checks find no stale calls to removed entry points.
- [ ] Documentation explains setup, native skill syntax, Default provider behavior, resume and Provider switch behavior.
- [ ] Automated tests cover the complete Daily loop with Claude only, Codex only and both Providers installed.
- [ ] A manual acceptance run uses dedicated non-sensitive Claude and Codex Work sessions.
- [ ] Manual acceptance verifies skill discovery, hook logging, same-Provider resume and a real Provider switch in both directions.
- [ ] Temporary tracker decisions are either promoted to durable documentation or identified for removal before merge.
