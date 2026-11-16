# Roadmap

Ideas for the next steps, roughly in order.

## Calendar reminders: test the import
The `calendar` channel is implemented (`tools/reminders.py ics`) but has not been tried with a real calendar yet.
- Import `data/deskmate-reminders.ics` into Google Calendar (Settings → Import & export) and into Apple Calendar.
- Check that the notification at event time survives the import: Google may drop alarms from imported files. If it does, document the manual fix in the README.
- Check what happens on a second import after changing times or days (update, duplicate, or delete-and-reimport) and document it.

## Slack reminders
A third reminder channel, `slack`: a plain message to a channel or to yourself through an [incoming webhook](https://api.slack.com/messaging/webhooks).
- The webhook URL is a secret: it goes in `data/config.json` (`reminders.slack_webhook`), never in the repo.
- Creating the Slack app may need a workspace admin's approval.
- Plain messages carry no buttons, so unlike the `mac` channel they don't record the answer in `data/log.csv`.

## License
Pick one after a first period of real use.

## Command names
`/call-it-a-day` is the current name for the evening skill. Alternatives considered: `/wrap-up`, `/punch-out`, `/end-of-shift`, `/sign-off`, `/lights-out`, `/pack-up`, `/log-off`.

## Version the project cards
Project cards live in `~/.claude/projects/<folder-key>/memory/`, outside any git repo, so an edit overwrites the old card with no way back (2026-11-12: closing the vlm-demo-builder card and moving its items to apps-monorepo needed hand-made `.bak` copies; Time Machine was not mounting).
- A local git repo in `~/.claude/projects` that tracks only `*/memory/*.md` (everything else ignored: transcripts are large and may hold secrets). Never pushed.
- `/checkpoint` and `/call-it-a-day` commit after writing a card, one commit per run, with the card's title in the message.
- Bonus: `git log -p` of a card shows how a project moved, which `/how-did-it-go` could use.
- Open: `feature/codex-cli-support` moves cards to `<DESKMATE_DATA_DIR>/projects/<key>/project-card.md`, with a revision number and one `card write` command for every write (the Claude path becomes a symlink). The approach above predates that; design it again before implementing.

## Install separately from the development checkout
Today the installed copy is the repository in `~/Dev/mc_dev/deskmate`, with personal data inside it (`docs/agents/release.md`). After `v0.3.0`, install from a clone pinned to a release tag, with the data in its own folder, so deploy and rollback become "move to tag, run `deskmate setup`".
- Setup must pass `DESKMATE_DATA_DIR` to the Claude and Codex hooks too; today only the reminders receive it, and hooks fall back to `<repo>/data`.
- Moving existing data is a setup migration with a backup, like the card and log migrations.
- Distribution as a Claude Code plugin was considered: it gives pinned, versioned copies for Claude, but Codex would still need its own install path. `deskmate setup` stays the single install point for both providers.
