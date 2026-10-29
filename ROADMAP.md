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

## Linux and Windows support
Keep the first Claude Code and Codex CLI integration macOS-only. Later, separate the portable daily loop from the macOS-specific desktop integration and add equivalents for session launching and reminders on Linux and Windows.

## Cross-provider analytics
Store Claude Code and Codex CLI measurements with their provider identity and analyse them separately at first. Later, define normalized metrics that support combined views and explicit Claude-versus-Codex comparisons without mixing incompatible raw token, context or compaction values.

## Structured project checks
Project cards currently contain flexible shell commands under `## Checks`, protected only by the read-only convention, Provider sandbox and a timeout. Replace or complement them with structured check types and an explicit allowlist so Deskmate can enforce non-mutating checks instead of trusting arbitrary shell text.

## External secret scanning for Provider switches
The first cross-provider switch implementation must apply conservative, local redaction before presenting a transfer bundle for approval. It must always tell the user which categories were removed and how many findings were redacted; it must never silently alter the bundle.

As defence in depth, evaluate an optional local secret scanner for a later release. The integration should:
- scan the temporary transfer bundle locally before either Provider receives it;
- use machine-readable findings without storing the bundle contents in the audit log;
- keep working with the built-in redaction if the optional scanner is unavailable;
- present findings and proposed removals for explicit user review;
- document false positives, false negatives and the fact that no scanner can guarantee that a bundle contains no secrets.

## License
Pick one after a first period of real use.

## Command names
`/call-it-a-day` is the current name for the evening skill. Alternatives considered: `/wrap-up`, `/punch-out`, `/end-of-shift`, `/sign-off`, `/lights-out`, `/pack-up`, `/log-off`.
