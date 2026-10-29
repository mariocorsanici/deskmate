# Provider-neutral Deskmate for Claude Code and Codex CLI

Status: ready-for-agent

## Problem Statement

Deskmate currently implements its Daily loop around Claude Code conventions, storage and transcripts. Its owner wants to keep working from the terminal while choosing Claude Code or Codex CLI according to availability, especially when one Provider runs out of tokens or quota. Today that change of Provider risks duplicating skills and Project cards, losing unrecorded work, mixing incompatible usage data, or depending on a full transcript that is costly to place in a new context and may contain secrets.

Deskmate therefore needs one provider-neutral core that preserves the current Claude behavior while adding Codex CLI as an equal Provider. It must share durable project state, bound the context transferred between Work sessions, degrade safely when transcripts are unavailable, and make Provider switches explicit and reviewable.

## Solution

Provide one stable `deskmate` command and one portable set of skills backed by a provider-neutral core. Claude Code and Codex CLI integrations become adapters responsible only for capabilities that actually differ: installation, hooks, Work session discovery, Session delta extraction, usage metrics, launch and resume.

Each Project has one shared Project card. A normal continuation resumes the Provider recorded by the card. An explicit Provider switch creates a new Work session with the other Provider from the Project card, current Checks and a bounded Session delta. It never pretends to resume the same cross-provider session.

The installer detects and validates the locally available Providers, installs one or both integrations, migrates existing Claude state atomically, and asks for a Default provider when needed. Native skill syntax remains `/skill` in Claude Code and `$skill` in Codex CLI.

Before a Session delta crosses the Provider boundary, Deskmate applies local secret redaction, presents a transfer manifest and asks for explicit consent. The temporary bundle is private, short-lived and excluded from audit content. Optional external secret scanning is deferred as defence in depth, not treated as proof that the bundle is safe.

## User Stories

1. As a Deskmate user, I want to run the same Daily loop with Claude Code or Codex CLI, so that Provider availability does not interrupt my work.
2. As a Deskmate user, I want one set of skills for both Providers, so that behavior does not drift between duplicate implementations.
3. As a Claude Code user, I want existing Deskmate behavior preserved after migration, so that adding Codex does not break my current routine.
4. As a terminal user, I want to invoke skills with each Provider's native syntax, so that Deskmate feels natural in both environments.
5. As a Deskmate user, I want one stable command for internal operations, so that skills and hooks do not encode Provider-specific scripts.
6. As a Deskmate user, I want the command available from my normal shell path, so that I can call it from any project.
7. As a user with only Claude Code installed, I want setup to install only the Claude integration, so that Codex is not required.
8. As a user with only Codex CLI installed, I want setup to install only the Codex integration, so that Claude is not required.
9. As a user with both Providers installed, I want setup to install both integrations, so that I can choose either one.
10. As a user with neither compatible Provider installed, I want setup to stop with an actionable explanation, so that it does not create a broken installation.
11. As a user running interactive setup with both Providers, I want to choose a Default provider, so that new work starts predictably.
12. As an automation author, I want non-interactive setup to require an explicit Default provider when both are available, so that automation never makes a hidden choice.
13. As a user, I want setup to validate Provider capabilities instead of checking only executable names, so that incompatible versions are identified.
14. As a user with one incompatible Provider and one compatible Provider, I want setup to install the compatible integration and explain the exclusion, so that one failure does not block all use.
15. As a user, I want installed Providers and the Default provider recorded in configuration, so that later commands use the same decisions.
16. As a user, I want one shared Project card per project, so that Claude and Codex see the same durable checkpoint.
17. As a user with existing Claude Project cards, I want them migrated automatically with a backup, so that no project history is lost.
18. As a Claude user after migration, I want the former Claude card location to resolve to the shared card, so that compatible Claude behavior continues without a second source of truth.
19. As a user, I want project identity derived from a readable slug plus a path-derived hash, so that cards remain recognizable without colliding.
20. As a user, I want Project cards to remain readable Markdown, so that I can inspect and edit durable project state.
21. As a Deskmate maintainer, I want restricted and validated Project card metadata, so that automation can rely on schema, revision and Provider identity.
22. As a user, I want concurrent Project card updates serialized and atomic, so that simultaneous Work sessions cannot silently overwrite each other.
23. As a user, I want a stale writer to reread the latest Project card, so that conflicts are handled from current state.
24. As a user, I want normal continuation to resume the Provider recorded in the Project card, so that Deskmate does not unexpectedly switch runtimes.
25. As a user, I want a missing recorded Provider to produce an explicit choice instead of silent fallback, so that a new Work session is intentional.
26. As a user, I want an explicit command to switch to the other Provider, so that I can continue when tokens or quota are exhausted.
27. As a user performing a Provider switch, I want Deskmate to create a new target Work session, so that session ownership remains truthful.
28. As a user, I want the Provider switch to use the shared Project card and current Checks, so that the target Provider starts from verified durable state.
29. As a user who could not create a final Checkpoint, I want the switch to include recent unrecorded progress, so that emergency failover remains useful.
30. As a user, I want the transferred Session delta bounded by message and character limits, so that the new context stays small.
31. As a user, I want one-off delta limit overrides, so that I can lower noise or selectively deepen context without changing configuration.
32. As a user, I want the delta to exclude metadata and raw tool output, so that the transfer emphasizes useful conversation content.
33. As a user, I want the delta to preserve both early and recent post-Checkpoint context, so that intent and latest state remain visible.
34. As a user, I want truncation, coverage and omitted counts disclosed, so that I know what the target Provider did not receive.
35. As a user, I want a Provider switch to continue from the Project card and Checks when the transcript is unavailable, so that transcript failure does not block work.
36. As a target Provider, I want to ask only for missing information after a degraded switch, so that the user can fill the gap efficiently.
37. As a user, I want a warning and confirmation before opening simultaneous Claude and Codex Work sessions for the same project, so that I understand the conflict risk.
38. As a user, I want a transfer preview showing source, target, Project card, included and omitted counts, size and redactions, so that I can make an informed consent decision.
39. As a user, I want likely secrets redacted locally before transfer, so that credentials are less likely to cross Provider boundaries.
40. As a user, I want every redaction reported by category and count, so that Deskmate never silently alters my context.
41. As a user, I want an uncertain secret finding to block the transfer, so that ambiguous sensitive content requires review.
42. As a user, I want to review, remove or replace a blocked finding, so that I remain in control of what is sent.
43. As a user, I want explicit consent required for each cross-provider transfer, so that no unattended option bypasses review in the first release.
44. As a user, I want the transfer bundle stored with private permissions, so that other local users cannot read it.
45. As a user, I want the target Work session to receive a bundle path rather than the bundle text in process arguments, so that content avoids shell history and process listings.
46. As a user, I want the bundle deleted after the target reads it, so that sensitive context is not retained unnecessarily.
47. As a user, I want abandoned bundles deleted after one hour, so that interrupted switches clean themselves up.
48. As a user, I want Provider-switch auditing to contain metadata but never transferred content, so that troubleshooting does not create another sensitive copy.
49. As a user, I want the Daily loop to continue with a warning if transcript extraction fails, so that optional analysis cannot stop core work.
50. As a user starting a retrospective, I want metrics, Handoffs, Project cards and logs inspected before messages, so that the initial analysis is cheap.
51. As a user, I want all candidate Work sessions listed and at most five recommended with reasons, so that retrospective scope is transparent.
52. As a user, I want to add, remove or replace recommended Work sessions before their deltas are read, so that I control context use.
53. As a user, I want deeper transcript reads performed progressively and one at a time, so that unclear points can be investigated without loading everything.
54. As a user, I want log rows to identify their Provider, so that Claude and Codex measurements are not confused.
55. As a user with historical logs, I want old rows preserved and attributed to Claude during migration, so that existing analytics remain meaningful.
56. As a user, I want Work session identity to combine Provider and Provider-native session ID, so that IDs from different runtimes cannot collide.
57. As a user, I want raw Provider analytics kept separate, so that incomparable token and context measurements are not combined misleadingly.
58. As a user, I want hooks merged idempotently into existing Provider configuration, so that rerunning setup neither duplicates nor erases unrelated hooks.
59. As a Codex user, I want setup to guide required trust or hook approval and verify logging, so that installation failures are visible immediately.
60. As a user, I want reminders to show both native invocation forms when both Providers are installed, with the default first, so that the next action is clear.
61. As a user, I want schema-aware atomic migrations with backups, so that configuration, cards and logs can recover from failed upgrades.
62. As a user with data from a newer unsupported schema, I want Deskmate to stop before mutation, so that older code cannot corrupt it.
63. As a user uninstalling Deskmate, I want integrations removed while personal data remains by default, so that uninstall is reversible.
64. As a user requesting data removal, I want a separate explicit purge confirmation, so that durable history is not deleted accidentally.
65. As a user, I want setup to remove obsolete Claude-only entry points after successful migration, so that there is one active architecture rather than a hidden compatibility layer.
66. As a user, I want setup and runtime implemented with the Python standard library, so that Deskmate does not require a package environment.
67. As a maintainer, I want synthetic Provider transcripts and an isolated home directory in tests, so that validation is deterministic and does not expose real sessions.
68. As a maintainer, I want the complete Daily loop tested through the stable command boundary for both Providers, so that adapters satisfy the same behavior.

## Implementation Decisions

- The supported environment for this feature is local terminal use on macOS with Claude Code, Codex CLI, or both. ChatGPT web and mobile are not Providers in this design.
- The provider-neutral core is one deep module exposed through a small `deskmate` command interface. Internal components cover shared state, session orchestration, Checks, launch behavior and Provider adapters; they are not separate user-facing APIs.
- Each Provider adapter implements session discovery, bounded Session delta reading, usage reading, new-session launch, same-provider resume and hook configuration.
- The command produces concise human-readable output by default and offers stable JSON output for skills, hooks and tests.
- One portable skill source is linked into each installed Provider's conventional skill directory. Claude-compatible frontmatter is retained and Codex metadata is added alongside it.
- Native invocation remains `/skill` for Claude Code and `$skill` for Codex CLI.
- Common setup replaces the Claude-only setup skill. The installer detects Providers, validates required capabilities and supports explicit Provider overrides.
- With both Providers present, interactive setup asks for the Default provider. Non-interactive setup must receive that choice explicitly.
- Installation records installed Providers and Default provider. Shell integration exposes the stable command from the user's local binary directory.
- Existing Claude behavior and data are migrated in a clean cut. There is no deprecation period because the system currently has one owner. Skills, hooks, reminders, documentation and installation are updated together, and obsolete entry points are removed.
- One Project card is stored in shared Deskmate data for each project. Existing Claude cards are backed up and migrated; the prior Claude location becomes a link to the shared card.
- A project key combines a readable directory slug with a hash of the canonical project path.
- Project cards remain Markdown with a restricted, validated metadata header containing schema version, revision and session ownership fields.
- Card writes use a lock and atomic replacement. Revision checks detect stale writers, which reread rather than silently overwrite.
- Flexible shell Checks remain for this release under the current read-only convention, Provider sandbox and timeout. Structured check types and an allowlist are future hardening.
- A normal resume uses the Provider recorded by the Project card. If it is unavailable, Deskmate offers to create a new Work session with an available Provider and never silently changes Providers.
- A Provider switch is a new Work session built from the Project card, current Checks and an optional Session delta. It is not a cross-provider resume.
- Switching while another Provider Work session for the same project may still be active requires a warning and explicit confirmation.
- The default Session delta limit is 12 messages and 6,000 characters. Limits are configurable and can be overridden for one command without mutating configuration.
- A Session delta contains only messages after the latest Checkpoint, excludes metadata and raw tool outputs, retains useful early context plus the most recent context, and reports truncation, coverage and included or omitted counts.
- Transcript extraction is best-effort. Failure produces a degraded switch from the Project card and Checks, and never blocks the rest of the Daily loop.
- Retrospective analysis is progressive: inspect structured durable data first, list all candidate Work sessions, recommend at most five with reasons, let the user change the selection, then read bounded deltas and deepen one session at a time only when needed.
- Logs gain a Provider column. Historical rows migrate as Claude, and Work session identity is the tuple of Provider plus native session ID.
- Provider-specific raw analytics remain separate. Future normalized combined and comparative views may be added without rewriting raw history.
- Hooks are merged into existing Provider configuration idempotently. Codex installation includes guidance for required approval or trust and an end-to-end logging check.
- Reminders show every installed Provider's invocation syntax and list the Default provider first.
- Configuration, Project cards and logs carry recognizable schema versions. Migrations create backups and replace files atomically. An unsupported future schema stops before any mutation.
- Cross-provider transfer applies deterministic local redaction before the preview. The preview shows source and target Providers, Project card identity, size, coverage, omissions, and redaction categories and counts.
- A possible secret that cannot be safely redacted blocks transfer for user review. No first-release non-interactive flag bypasses preview and consent.
- The approved transfer bundle is created in a private temporary location with mode `0600`. Only its path is passed to the target Provider. The target reads and deletes it; later Deskmate commands remove abandoned bundles older than one hour.
- Provider-switch audit events record only metadata such as source, target, time, outcome, size and redaction counts. They never record bundle or finding contents.
- Optional integration with a local external secret scanner is deferred. It is defence in depth, must preserve built-in redaction as a fallback, must report findings, and must not claim that a clean result guarantees absence of secrets.
- The runtime uses the Python standard library only. Existing operating-system tools remain allowed where the current macOS integration requires them.
- Uninstall removes Provider integrations but preserves data by default. It separately asks whether to purge data, defaults to no, and requires the exact confirmation `DELETE`; non-interactive uninstall preserves data unless an explicit purge option is given.
- Temporary local tracker material is retained on the feature branch for implementation and removed or promoted to durable documentation before merge.

## Testing Decisions

- Tests assert externally visible behavior through the stable `deskmate` command wherever possible. Adapter internals are not tested independently when the same behavior can be observed at the command seam.
- The primary seam is the command boundary with an isolated temporary home directory, temporary Deskmate data and synthetic Claude and Codex session stores.
- Contract scenarios run against both Provider adapters: detection, capability validation, session discovery, usage extraction, bounded delta extraction, new launch, same-provider resume and hook configuration.
- Daily loop scenarios cover morning planning, Checkpoint creation, retrospective selection and evening Handoff with each Provider independently and with both installed.
- Migration tests start from representative current Claude configuration, cards and logs; verify backups, new schemas, historical Provider attribution and preserved content; and exercise interruption or invalid input without partial replacement.
- Idempotency tests rerun installation and hook configuration and verify that Deskmate entries are not duplicated and unrelated user configuration remains intact.
- Project identity tests cover equivalent canonical paths, readable slugs and collision resistance between same-named directories.
- Project card tests exercise valid reads and writes, invalid metadata, schema rejection, revision conflicts, lock behavior and atomic replacement.
- Provider-switch tests verify normal transfer, emergency transfer without a final Checkpoint, transcript-unavailable degradation, missing source Provider, simultaneous-session confirmation and target launch failure.
- Session delta tests cover the latest Checkpoint boundary, default and one-off limits, early-plus-recent selection, exclusion of raw tool output, Unicode, truncation disclosure and exact included or omitted counts.
- Secret-handling tests use synthetic canary values only. They verify deterministic redaction, category and count reporting, blocking of uncertain findings, explicit consent, absence of content from audit records and refusal of unattended bypasses.
- Temporary-bundle tests verify mode `0600`, path-only handoff, deletion after consumption and cleanup after the one-hour expiry without deleting unrelated files.
- Log tests cover the Provider column, provider-plus-session identity, atomic migration, legacy attribution and separation of raw analytics.
- Setup tests cover no Provider, each Provider alone, both Providers, an incompatible Provider, interactive defaults and non-interactive refusal without an explicit default.
- Uninstall tests verify data preservation by default, refusal of an incorrect purge confirmation and explicit purge behavior using only isolated test data.
- A final manual acceptance run uses dedicated non-sensitive Claude and Codex Work sessions to validate native skill discovery, hook approval, logging, same-provider resume and a real Provider switch.
- Existing command-line and temporary-directory testing patterns are reused where present. New tests establish the command boundary as the preferred prior art for later Provider features.

## Out of Scope

- ChatGPT web, ChatGPT mobile and other agent runtimes.
- Linux and Windows support.
- Seamlessly resuming the same native Work session in a different Provider.
- Sending an entire transcript to the target Provider.
- Combining incompatible raw Claude and Codex usage measurements.
- Normalized cross-provider analytics or comparative dashboards.
- Structured replacement of arbitrary shell Checks.
- Mandatory external secret-scanner installation or execution.
- A guarantee that secret detection catches every credential.
- A non-interactive bypass for cross-provider transfer consent.
- A long compatibility or deprecation period for replaced Claude-only entry points.
- Third-party Python runtime dependencies, package environments or services.

## Further Notes

- The primary motivation for Provider switching is graceful continuation when the active Provider exhausts tokens or quota and may no longer be able to create a fresh Checkpoint.
- The Project card is the durable source of truth. A Session delta is bounded recovery context, not another durable transcript store.
- External scanner research recommends Gitleaks as a possible future primary gate because it supports stdin and machine-readable reports, with `detect-secrets` in offline mode as an optional independent second opinion. Either remains heuristic and may produce false positives or false negatives.
- Future work may add Linux and Windows adapters, structured Check hardening, and normalized combined or comparative analytics while retaining Provider identity.
