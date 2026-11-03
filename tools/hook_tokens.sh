#!/bin/zsh
# Historical Claude Stop hook delegates to the provider-aware usage updater.
root=${0:A:h:h}
exec "$root/bin/deskmate" hook-event --provider claude
