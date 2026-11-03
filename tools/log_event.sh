#!/bin/zsh
# Historical shell callers share the provider-aware CSV writer.
root=${0:A:h:h}
exec python3 -I "$root/tools/activity_log.py" event "$@"
