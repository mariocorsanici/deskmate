# Daily loop tuning: live state, honest metrics, retrospective cadence

Status: ready-for-agent

## Problem Statement

On 2026-11-06 `/whats-on-today` proposed work that was already done. The handoff was from Wednesday evening, Thursday was a travel day, and in between Gio merged six Fleet PRs and vlm PR #63 was merged. The card checks compared against stale `origin/...` refs (fixed on `develop` in `70468e3`: `check.py` now fetches every repo a card names) and read ticket files from the working tree, which a fetch does not update.

The same review found three more gaps:
- the token figures in `data/log.csv` count a skill run until the next `/command` of the session, so they include unrelated work done after the skill (e.g. a `/checkpoint` row with 182 turns and 96M tokens);
- retrospectives were skipped on busy days (none between 2026-10-30 and 2026-11-06), so running experiments went unverified;
- the day has no explicit goal and no record of why the user switched project.

## Solution

Small, independent changes to the existing skills and tools, one ticket each. Tickets 01–08 are ready. Tickets 05–07 were confirmed at `/how-did-it-go` on 2026-11-06. Ticket 08 (morning login check) came from the same retrospective.

## Branching and dependencies

- Branch `feature/daily-loop-tuning`, from `develop` at `70468e3`.
- `feature/codex-cli-support` rewrites the same skills and moves project cards to `data/projects/`. Merge this branch into `develop` **after** `feature/codex-cli-support` has landed, rebasing first and resolving conflicts there. Write changes so they survive that move: describe card locations through the same helper/constant the codex branch uses, not hardcoded `~/.claude/projects` paths, when possible.
- Follow `docs/agents/development-workflow.md`: focused commits per ticket, tests per ticket, update the ticket file, push the branch at each ticket boundary.

## Out of scope

- Slack: deskmate never reads Slack unless the user asks.
- Changing what the user sees in English vs Italian: replies keep following `config.json` `language`.
