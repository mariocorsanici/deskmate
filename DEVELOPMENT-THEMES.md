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
| 2026-11-24 | `475da0f3` | The topic as the unit: a larger object (a PR, a task, a study) that holds its sessions and tabs, so that the sessions created by `/clear` trace back to the same topic; for PR sessions and development sessions alike | Open question in ROADMAP item 1; themes 3 and 4 |
| 2026-11-24 | `475da0f3` | Study streams managed like projects: a card per stream (e.g. domyn-agents) recording progress, notes written and next steps, read by `/whats-on-today` and updated by `/checkpoint`; today study is planned less rigorously than development and gets postponed | Theme 1 |
| 2026-11-24 | `475da0f3` | `open_tab.sh` should not bring the new tab to the front: today iTerm switches to it by itself. Make focus configurable in `config.json`, off by default | Not assigned to a theme |
| 2026-11-24 | `475da0f3` | A notification, like the Deskmate reminders, when a session opened by `open_tab.sh` is ready (start-up done, waiting for input); configurable, together with the focus option above | Not assigned to a theme |

## The four themes (2026-11-23)

1. **Project history and evidence of contribution.** A history that documents
   the developments of each project, lets them be analysed, and produces a
   document showing the contribution made. Takes up the 2026-11-18 idea:
   projects made of several sessions, each feeding a project status file;
   sessions listable from it and searchable by title. Includes study streams
   (2026-11-24): each stream gets a card like a project, with its progress,
   so study is planned and tracked like development instead of being
   postponed. To decide: how a stream card relates to `study-later.md` (a
   topic there could graduate into a stream) and to the project it serves.
2. **Daily journal.** Use a Deskmate session as a journal, to keep better track
   of project management, problems and secondary tasks. Extends the "Daily
   journal" draft and includes the length of the handoff (2026-11-17).
3. **Roles of sessions and cards.** Define them better, in order to:
   - reset sessions without losing context;
   - plan the day's activities per session;
   - plan when to use more or less capable models and agents;
   - use `/clear` strategically;
   - trace the sessions created by `/clear` back to their topic (2026-11-24).
     After `/clear` Claude Code starts a new session ID in the same tab, so
     Deskmate counts it as a separate session. Two candidate designs:
     - **The tab as the thread:** the session-start hook also logs the tab's
       identity, and the tab title set by `open_tab.sh` names the topic.
       Simplest; first verify that the tab identity reaches the hook (Deskmate
       does not use it anywhere today).
     - **The topic as an object:** a PR, task or study with its own card or
       section that holds its sessions and tabs; `/checkpoint` and
       `/call-it-a-day` reason per topic. A topic may span tabs and a tab may
       change topic, so it needs design.

   Takes up the task–session pair (2026-11-18), the session weight at
   `/checkpoint` (2026-11-19) and the 30-prompt cap experiment in
   `data/lessons.md`.
4. **PR review sessions.** Manage the sessions dedicated to PRs better. Needs a
   brainstorming session before any design. Takes up the 2026-11-17 idea and
   the evidence in `data/lessons.md`:
   - PRs checked from up to three sessions a day (2026-11-19 and 20);
   - a PR session that is always resumed accumulates useless context;
   - PRs checked from three sessions on 2026-11-23, partly `/clear` in the same
     tab; the agent must reread reviewers' replies to answer or review, so
     rereading PR state is legitimate;
   - current experiment (from 2026-11-24): one PR tab a day, `/clear` inside it
     allowed, no PR questions from other sessions.

**Order:** decided by the open question "the day as the frame, or the session
as the unit". A third answer emerged on 2026-11-24: **the topic as the unit,
inside the day**.
- Theme 2 is the day as the frame.
- Theme 3 is the session (or the topic) as the unit.
- Theme 1 depends on both.
- Theme 4 is a concrete case of theme 3.
