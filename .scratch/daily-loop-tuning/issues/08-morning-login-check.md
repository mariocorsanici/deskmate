# 08: Morning login check, all fixes at once

**Status:** ready-for-agent

In the period 2026-10-31 → 2026-11-06, expired or missing logins showed up one at a time, in the middle of work:
- 1Password and Touch ID on 3/11 at 09:15 and 09:48;
- the GitHub SSH key on 4/11 at 11:48;
- gcloud on 6/11 at 10:17.

In October, the Bitbucket key had the same pattern, until a morning check covered it. The user wants to do all logins at the start of the day.

- [ ] A project card can list the logins its work needs, in a `Logins` line or section, e.g. `ssh-key ~/.ssh/domyn_key_github`, `gcloud`, `gcloud-adc`, `1password`.
- [ ] A read-only tool (in `check.py` or a new `tools/logins.py`) checks each one without prompting or changing anything:
  - `ssh-key`: `ssh-add -l` lists the key's fingerprint;
  - `gcloud`: `gcloud auth print-access-token` exits 0;
  - `gcloud-adc`: `gcloud auth application-default print-access-token` exits 0;
  - `1password`: `op whoami` exits 0.
  - It never prints a token or secret: exit codes only.
  - Each check has a short timeout.
- [ ] `/whats-on-today` runs it for the projects proposed for the day, deduplicates across cards, and shows one block "Login da fare" with the exact `! <command>` lines, before the suggested order. If everything is valid, it prints one line saying so.
  - The fix commands are `ssh-add <key>`, `gcloud auth login`, `gcloud auth application-default login`, and an `op` command that reads a secret, so Touch ID appears.
  - For 1Password: with the desktop-app integration, `op whoami` reports "not signed in" until a command reads a secret, and the authorization is per terminal process. Report this as a warning, not a failure, and say that Touch ID will show up at the first secret read.
- [ ] The existing cards for Fleet Shipment Manager and vlm-demo-builder get their `Logins` (the user confirms the list).
- [ ] Tests: a fake card with logins, where the check commands are stubbed to pass or fail, produces the right block and never runs a fix command.

Out of scope: secrets that Claude Code's safety checks block on purpose, such as pasting a connector key into a web form. The clipboard workaround stays.

## Comments
