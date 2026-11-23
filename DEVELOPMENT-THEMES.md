# Development themes

Written on 2026-11-23 from the `/whats-on-today` session `7384ab81`. Ideas for
Deskmate proposed in conversations that never reached the repository, with
their origin, and the four themes they were grouped into. Not a plan: the
priorities are in [ROADMAP.md](ROADMAP.md), which takes items from here as
drafts when they are ready to explore.

## Why this exists
Several ideas proposed in conversations never reached the repository. Some
were in the Deskmate project card and were lost when the card was rewritten.
This file collects them all, with their origin.

## Ideas found in conversations

| Date | Session | Idea | Status |
|---|---|---|---|
| 2026-11-06 | `d28cb5f8` | Tell development apart from travel, office days and documentation | Done: `/agenda` |
| 2026-11-15 | `9dd68833` | Version the project cards | Dropped (ROADMAP, "Dropped") |
| 2026-11-17 | `22485f64` | One session dedicated to PR reviews, mine and other people's | Only an experiment in `data/lessons.md` |
| 2026-11-17 | `22485f64` | Evaluate the length and complexity of the handoff | Never written in the repository |
| 2026-11-18 | `22485f64` | Task–session pair: one session per task, a check on the task's scope, a closing skill with a checkpoint; projects made of sessions that update a status file; sessions listable and searchable by title; evidence of the work done | Never written in the repository (lost from the card) |
| 2026-11-19 | `7bf85f95` | `/checkpoint` measures the session's weight and suggests whether and where to `/clear`, with the files to resume from and the restart prompt; the same for planning and brainstorming sessions | Never written in the repository |
| 2026-11-23 | `d9593dbe` | The first session of the day as a journal | In ROADMAP as a draft ("Daily journal") |

## The four themes (2026-11-23)

1. **Project history and evidence of contribution.** A history that documents
   the developments of each project, lets them be analysed, and produces a
   document showing the contribution made. Takes up the 2026-11-18 idea:
   projects made of several sessions, each feeding a project status file;
   sessions listable from it and searchable by title.
2. **Daily journal.** Use a Deskmate session as a journal, to keep better track
   of project management, problems and secondary tasks. Extends the "Daily
   journal" draft and includes the length of the handoff (2026-11-17).
3. **Roles of sessions and cards.** Define them better, in order to:
   - reset sessions without losing context;
   - plan the day's activities per session;
   - plan when to use more or less capable models and agents;
   - use `/clear` strategically.

   Takes up the task–session pair (2026-11-18), the session weight at
   `/checkpoint` (2026-11-19) and the 30-prompt cap experiment in
   `data/lessons.md`.
4. **PR review sessions.** Manage the sessions dedicated to PRs better. Needs a
   brainstorming session before any design. Takes up the 2026-11-17 idea and
   the evidence in `data/lessons.md`:
   - PRs checked from up to three sessions a day (2026-11-19 and 20);
   - a PR session that is always resumed accumulates useless context;
   - current experiment: one new PR session a day, its state in the card,
     long PRs read by a subagent.

**Order:** decided by the open question "the day as the frame, or the session
as the unit".
- Theme 2 is the day as the frame.
- Theme 3 is the session as the unit.
- Theme 1 depends on both.
- Theme 4 is a concrete case of theme 3.
