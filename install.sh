#!/bin/zsh
# Common provider-neutral setup/removal. Preferences and data stay in data/.
set -e
root=${0:A:h}
operation=setup
arguments=()
for argument in "$@"; do
  if [[ $argument == --remove ]]; then
    operation=remove
  else
    arguments+=("$argument")
  fi
done
exec python3 -I "$root/bin/deskmate" "$operation" "${arguments[@]}"
