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
