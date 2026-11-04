# Provider-neutral CLI — progress and early manual checks

Updated: 2026-11-04
Integration branch: `feature/codex-cli-support`
Latest work: ticket 07, recorded-provider routing and confirmed native ownership (2026-11-04).

## Progress

Tickets **01–07 are complete** on the integration branch:

- 01–02: provider-neutral CLI and provider detection/configuration.
- 03: shared Project cards with revision checks and safe Claude migration.
- 04: Claude adapter, skill discovery, hooks, sessions and launch/resume.
- 05: Codex adapter, native skill metadata, hooks, sessions and launch/resume.
- 06: provider-aware logs, migrations and separate usage metrics.
- 07: recorded-provider routing, explicit lost-session recovery and revision-safe native ownership confirmation.

The 01–06 automated suite passed **105 tests**, with no skips and Python `ResourceWarning`s treated as errors. Independent Standards and Spec reviews found no remaining material issues. Claude’s native skill discovery and hook delivery were also verified in a disposable configuration with a synthetic API key; no model request was made.

Ticket 07 validation passed **128 tests**, including 23 new routing/lifecycle cases, with no skips and ResourceWarnings as errors.

Tickets **08–14 have not started**. Ticket 07 adds isolated public-command tests for routing, journal concurrency, early/late hooks and ownership recovery. The feature branch is local and has not been pushed or merged into `develop` or `main`. The complete authenticated Daily-loop acceptance belongs to ticket 14.

## Early manual checks

These are a small smoke test for the completed adapter work. They are useful before 07–13 because they can expose integration problems in native skill discovery, hooks, shared cards and provider attribution. They do not validate provider routing, cross-provider context transfer, redaction/consent, installation migration or the full Daily loop; those depend on later tickets.

### Preparation

1. Use a disposable project directory with no sensitive files and a fresh Deskmate data directory. Keep the existing installation and personal project cards untouched.
2. Use the installed local Claude Code and Codex CLI accounts only for interactive checks. Review each provider’s trust/approval prompt normally; do not bypass permissions. If an account or required trust setup is unavailable, record that check as blocked rather than substituting synthetic test evidence.
3. Create a small test file such as `manual-probe.txt` in the disposable project. Record the test project path and the selected provider for each step.

### Check A — skill discovery and hook attribution

For each provider, start a native Work session in the disposable project and confirm that the five shared Deskmate skills are discoverable with the native syntax: `/checkpoint` in Claude and `$checkpoint` in Codex. Invoke one harmless skill (for example, `/study-later manual probe` or `$study-later manual probe`) and finish the turn normally.

**Pass:** the provider recognizes the skill; `data/log.csv` receives the expected event with the correct provider, native session ID and disposable project path. Unrelated personal hooks/configuration remain unchanged.

### Check B — shared Project card visibility

In the Claude session, run `/checkpoint` and save a status that names `manual-probe.txt`. Then open the same disposable project in Codex, read the shared Project card, and run the card’s Checks. Confirm that the Claude checkpoint and its provider/session ownership are visible. If safe and supported by the current skill instructions, checkpoint the same project from Codex and re-read the single shared card from Claude.

**Pass:** both providers resolve the same card path and see the latest saved status; there is one shared card, and each successful write records the provider/session that made it.

### Check C — provider-specific usage reporting

Run a short, ordinary turn in each provider, then allow the normal stop hook to run. Ask Deskmate for provider-separated metrics (or inspect `deskmate metrics --provider all`).

**Pass:** Claude and Codex appear under separate provider entries with their native session IDs; available usage is attributed to the matching provider and no usage is combined across providers. If a provider does not expose a counter for that session, the report identifies it as unavailable/degraded instead of inventing a value.

### Recording results and cleanup

Record the date, provider/CLI versions, test project path, commands used, observed log/card result, and any blocked or failed check. Remove only the disposable project and test data after confirming the paths; retain evidence without credentials or transcript contents. Report failures before continuing with tickets 07–13, since those tickets depend on the adapters, shared cards and usage data tested here.

No manual checks above have been run yet. On 2026-11-04 the owner explicitly postponed them to preserve Claude token quota; continue synthetic implementation/testing without making native model requests. Automated tests and the prior isolated Claude discovery/hook probe are not substitutes for these user-account manual checks.
