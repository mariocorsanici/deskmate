#!/bin/zsh
# Historical Claude hook configuration delegates to the stable command.
root=${0:A:h:h}
exec "$root/bin/deskmate" hook-event --provider claude
