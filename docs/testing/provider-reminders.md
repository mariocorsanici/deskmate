# Provider-aware reminder verification

Current follow-up: [C16 morning recovery](premerge-morning-2026-11-15.md) adds
working-day RunAtLoad and once-per-date claiming and records actual native
display, concurrent suppression and same-day LaunchAgent reload. The C12
results below describe their original date.

C12, verified 2026-11-09 on `feature/codex-cli-support`, starting from `8e34b5a`.

## Behavior

The existing morning/evening templates render the configured installed Providers:
Claude Code uses `/skill`, Codex CLI uses `$skill`. Both appear in dual setups,
with the configured Default provider first regardless of installed-list order.
Each study-later invocation retains `<topic>` or `<argomento>`.

English/Italian wording, unsupported-language English fallback, buttons, topic
counts, retrospective weekdays, time windows and LaunchAgent schedules retain
existing behavior. Calendar descriptions use the same renderer with static topic
text and retrospective weekdays; escaping, UTF-8 folding and idempotent calendar
regeneration are retained. A Provider change regenerates the calendar file;
reimport it after configuration changes. Slack remains planned.

Desktop scripts use the public `deskmate reminders` command. Ordinary `text` output
keeps its line protocol. `text <kind> --with-provider` appends the displayed Default
provider from the same configuration snapshot. Scripts pass this identity to
`respond <kind> <answer> --provider claude|codex`, preserving attribution even when
configuration changes while the alert is open. Each snoozed alert gets a fresh
snapshot. These reminder rows do not claim native skill execution: their session
and cwd are empty. Calendar events do not log responses.

Legacy configuration without `providers` retains Claude syntax. Invalid Provider
selection fails with `deskmate configure` guidance; malformed/future configuration
uses the shared reader's errors. Log CSV errors return a concise status 2 without
mutating the log.

## Evidence

Baseline: 180 tests passed. New feature tests first reproduced missing Codex
invocations, missing dual forms/default ordering and incorrect Claude-only
response attribution. Follow-up regressions observed RED for incomplete dual
study-later arguments, configuration changes during an alert, and malformed CSV
error reporting; all passed after fixes.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -Werror::ResourceWarning -m unittest discover -s tests -q
# Python 3.14.6: 193 tests, OK

PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -Werror::ResourceWarning -m unittest tests.test_reminders -q
# Python 3.9.6: 13 tests, OK
```

`tests/test_reminders.py` invokes the public CLI and actual zsh wrappers in
temporary homes/data directories. Only desktop notification and sleep boundaries
are replaced with fake commands; no real notifications, calendar imports, model
requests or installed personal configuration changes are performed. Tests check
both Providers/defaults, localization, arguments, calendar bytes and refresh,
legacy/invalid configuration, recorded identity, changed configuration, snooze,
ignored responses, dry runs, schedule and log error preservation.

One independent read-only review verified the ticket's boundaries, including
literal dollar syntax through zsh and invalid configuration preventing GUI calls.
Its attribution race and CSV error regression were reproduced and fixed with
regressions. Actual desktop display, calendar application import and authenticated
native acceptance remain pending and are not inferred from these tests.
