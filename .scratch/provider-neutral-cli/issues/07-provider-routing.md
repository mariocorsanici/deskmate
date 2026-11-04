# 07: Route Work session launch and resume

**What to build:** Start or continue work with a predictable Provider: resume with the Provider recorded by the Project card and use the Default provider only when there is no owned Work session.

**Blocked by:** 02: Detect and configure Providers; 03: Migrate to shared Project cards; 04: Put Claude behind the Provider adapter; 05: Add the Codex Provider adapter.

**Status:** ready-for-agent

**Implementation:** complete (automated acceptance; native manual acceptance postponed).

- [x] A Project card with an available recorded Provider resumes through that Provider.
- [x] A project without an owned Work session starts with the Default provider. A recorded but unrecoverable Work session requires an explicit new-session choice.
- [x] An unavailable recorded Provider never causes a silent switch.
- [x] When the recorded Provider is unavailable, Deskmate explains the condition and offers an explicit new Work session with an available Provider.
- [x] Launch and resume update Project card ownership consistently.
- [x] Human and JSON output distinguish resume, new session and refused implicit switch.
- [x] Attempts to launch simultaneous Work sessions for one project can be detected by later switch behavior.


## Comments

2026-11-04: The owner approved explicit recovery when a recorded session is lost,
including when the Default provider differs. Approved design and plan are in
`docs/superpowers/specs/2026-11-04-provider-routing-design.md` and
`docs/superpowers/plans/2026-11-04-provider-routing.md`.

Implemented `deskmate work-session`: recorded-provider resume, default new-session
routing, canonical-folder/native-identity validation independent of analytics,
human/JSON outcomes, explicit `--new --provider` recovery and read-only dry runs.
Per-project schema-1 launch journals correlate attempts to SessionStart or first
UserPromptSubmit through `DESKMATE_LAUNCH_ID`; terminal submission alone stays
pending. SessionEnd preserves history. Ownership uses revision-checked atomic
metadata updates, preserving Markdown and never inventing a session ID.

Isolated public-command tests cover both Providers, missing runtimes/sessions,
wrong folders, early hooks before terminal completion, launch failure after early
identity evidence, repeated/unrelated hooks, stale Checkpoints, concurrent
launches, partial-publication recovery, future/invalid schemas and shell-sensitive
paths/prompts. No authenticated native Work session was launched, no model request
was made and no personal state was read or modified. Early smoke checks and full
native Daily-loop acceptance remain pending by the owner's request to preserve
Claude quota. Later Provider-switch confirmation/transfer remains ticket 09.

Automated validation: `python3 -Werror::ResourceWarning -m unittest discover -s tests -q` passed **132 tests, no skips**, including 27 new public routing/lifecycle tests.

Independent final review found three important regressions, each reproduced
through the public command before fixing: late native identity after terminal
failure was dropped, Claude's lossy legacy folder key permitted a wrong-folder
resume, and focusing an existing Claude tab created an unconfirmable attempt.
The fixes preserve late/uncertain launch evidence without claiming ownership,
require trustworthy indexed Claude folder identity, and report focus with the
existing native identity while preserving the card. Matching SessionEnd closes
all attempts for that native session. Uncertain terminal submission is separately
tested for both Providers. All four added regression scenarios were observed RED
before the corresponding fixes. No Critical or Minor findings were reported.
