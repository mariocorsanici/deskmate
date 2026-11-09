# 12: Update reminders for both Providers

**What to build:** Make every Deskmate reminder tell the user how to perform the next action with the Providers actually installed, while keeping the Default provider most prominent.

**Blocked by:** 02: Detect and configure Providers; 07: Route Work session launch and resume.

**Status:** ready-for-agent

- [x] A single-Provider installation shows only that Provider's native skill syntax.
- [x] A dual-Provider installation shows both invocation forms.
- [x] The Default provider is shown first.
- [x] Reminder responses continue to log correctly with Provider identity where applicable.
- [x] Existing reminder channels retain their current behavior apart from Provider-aware wording.
- [x] Reminder tests use isolated configuration and do not create real desktop or calendar notifications.


**Implementation:** complete on 2026-11-09; see `docs/testing/provider-reminders.md`.

## Comments

- 2026-11-09: session `/root` resumed C12 on `feature/codex-cli-support` from
  `8e34b5a`. Baseline 180/180 passed. Existing approved core-completion plan,
  Task 3, governs this ticket; C13 and authenticated native acceptance remain pending.
- Reminder rendering uses configured installed Providers, with Default provider
  first. Legacy configurations without `providers` retain Claude syntax; invalid
  Provider settings fail with guidance to run `deskmate configure`.
- Desktop response attribution means the Default provider actually displayed,
  not evidence that a native skill ran. The rendered Provider is retained through
  the alert even if configuration changes before the user responds. No native
  session or cwd is fabricated. Calendar events remain non-logging.
- Acceptance: full suite 193/193 on Python 3.14.6; 13/13 reminder tests also on
  system Python 3.9.6. Focused scenarios observed RED before implementation/fixes.
  Independent review's attribution race and CSV error regression both have
  RED/GREEN regressions; dual study-later forms retain their argument.
