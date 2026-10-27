#!/bin/zsh
# Opens a Claude Code session in a new iTerm tab with a fixed title, used by /whats-on-today.
# Usage: open_tab.sh <title> <folder> <session-id>
# Title format: "<project> <ticket> · <what to do>", e.g. "Basler CAT-207 · test camera".
# The tab sets its title with an escape sequence (iTerm's own session name gets replaced by the job name)
# and runs Claude Code with CLAUDE_CODE_DISABLE_TERMINAL_TITLE=1, which would overwrite it otherwise.
# DESKMATE_DRY_RUN=1 prints the command instead of opening the tab.

if (( $# != 3 )); then print -u2 "usage: ${0:t} <title> <folder> <session-id>"; exit 2; fi
title=$1 folder=${~2} id=$3
[[ -d $folder ]] || { print -u2 "${0:t}: no such folder: $folder"; exit 1; }

command="printf '\\e]0;%s\\a' ${(q)title}; cd ${(q)folder} && CLAUDE_CODE_DISABLE_TERMINAL_TITLE=1 claude --resume ${(q)id}"
if [[ -n $DESKMATE_DRY_RUN ]]; then print -r -- "[$title] $command"; exit 0; fi

osascript - "$command" <<'EOF'
on run argv
  tell application "iTerm"
    activate
    if (count of windows) = 0 then create window with default profile
    tell current window
      set t to (create tab with default profile)
      tell current session of t to write text (item 1 of argv)
    end tell
  end tell
end run
EOF
