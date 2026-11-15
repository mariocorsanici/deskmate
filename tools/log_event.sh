#!/bin/zsh
# Appends an activity row, preserving legacy/extension columns under one lock.
# Usage: log_event.sh <event> [detail] [session] [cwd]
# An empty detail on a Deskmate <skill>-end event becomes a precise UTC timestamp.
python3 -I "${0:A:h}/usage_log.py" "$@"
