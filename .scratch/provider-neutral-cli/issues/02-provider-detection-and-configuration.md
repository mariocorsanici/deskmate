# 02: Detect and configure Providers

**What to build:** Let Deskmate discover compatible Claude Code and Codex CLI installations, record the available Providers, and select a Default provider without making hidden choices.

**Blocked by:** 01: Introduce the provider-neutral command.

**Status:** ready-for-agent

- [ ] Detection validates the capabilities Deskmate needs instead of checking only executable names.
- [ ] Claude-only, Codex-only, both-compatible, one-incompatible and neither-compatible scenarios have distinct actionable results.
- [ ] Interactive configuration asks for a Default provider when both are compatible.
- [ ] Non-interactive configuration with both Providers stops unless the Default provider is supplied explicitly.
- [ ] Configuration records its schema version, installed Providers and Default provider.
- [ ] A configuration using an unsupported future schema is rejected before mutation.
- [ ] Human and JSON output report included and excluded Providers with reasons.

