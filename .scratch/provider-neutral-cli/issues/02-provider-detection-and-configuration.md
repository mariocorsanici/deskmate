# 02: Detect and configure Providers

**What to build:** Let Deskmate discover compatible Claude Code and Codex CLI installations, record the available Providers, and select a Default provider without making hidden choices.

**Blocked by:** 01: Introduce the provider-neutral command.

**Status:** ready-for-agent

**Implementation:** complete

- [x] Detection validates the capabilities Deskmate needs instead of checking only executable names.
- [x] Claude-only, Codex-only, both-compatible, one-incompatible and neither-compatible scenarios have distinct actionable results.
- [x] Interactive configuration asks for a Default provider when both are compatible.
- [x] Non-interactive configuration with both Providers stops unless the Default provider is supplied explicitly.
- [x] Configuration records its schema version, installed Providers and Default provider.
- [x] A configuration using an unsupported future schema is rejected before mutation.
- [x] Human and JSON output report included and excluded Providers with reasons.

## Comments

Implemented `deskmate providers` and `deskmate configure` through the stable
command boundary. Detection runs bounded, identity-checked version probes;
configuration preserves legacy preferences, writes atomically, is idempotent,
and refuses malformed or unsupported future schemas before mutation.

