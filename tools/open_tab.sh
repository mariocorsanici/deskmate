#!/bin/zsh
# Opens a Claude Code session in a new iTerm tab with a fixed title, used by /whats-on-today.
# Usage: open_tab.sh <title> <folder> <session-id>
#        open_tab.sh --new <title> <folder> [prompt]   new session in that folder, started with the prompt
#        (experiment fresh_sessions: the new session picks up from the project card instead of the old conversation)
# Title format: "<project> <ticket> · <what to do>", e.g. "Basler CAT-207 · test camera".
# The tab sets its title with an escape sequence (iTerm's own session name gets replaced by the job name)
# and runs Claude Code with CLAUDE_CODE_DISABLE_TERMINAL_TITLE=1, which would overwrite it otherwise.
# If the session is already running in an iTerm tab, it brings that tab to the front instead:
# two processes on the same session would split it in two.
# DESKMATE_DRY_RUN=1 prints the command instead of opening the tab.

new=
[[ $1 == --new ]] && { new=1; shift }
if (( $# != 3 && !(new && $# == 2) )); then
  print -u2 "usage: ${0:t} <title> <folder> <session-id>\n       ${0:t} --new <title> <folder> [prompt]"; exit 2
fi
title=$1 folder=${~2}
if [[ -n $new ]]; then
  id= prompt=${3:-"Pick up this project from its project card: read the Status section, check it with the Checks, and tell me where we start."}
else
  id=$3
fi
[[ -d $folder ]] || { print -u2 "${0:t}: no such folder: $folder"; exit 1; }

pid=$([[ -n $id ]] && pgrep -f "claude --resume $id" | head -1)
if [[ -n $pid ]]; then
  tty=/dev/$(ps -o tty= -p $pid | tr -d ' ')
  if [[ -n $DESKMATE_DRY_RUN ]]; then print -r -- "[$title] already running on $tty"; exit 0; fi
  found=$(osascript - "$tty" <<'EOF'
on run argv
  tell application "iTerm"
    repeat with w in windows
      repeat with t in tabs of w
        repeat with s in sessions of t
          if tty of s is (item 1 of argv) then
            select w
            tell t to select
            activate
            return "yes"
          end if
        end repeat
      end repeat
    end repeat
  end tell
  return "no"
end run
EOF
)
  [[ $found == yes ]] && { print "${0:t}: $id is already running, its tab is now in front"; exit 0 }
  print -u2 "${0:t}: $id is already running (pid $pid, $tty) outside iTerm: close it before opening it again"; exit 1
fi

if [[ -n $new ]]; then launch="claude ${(q)prompt}"; else launch="claude --resume ${(q)id}"; fi
command="printf '\\e]0;%s\\a' ${(q)title}; cd ${(q)folder} && CLAUDE_CODE_DISABLE_TERMINAL_TITLE=1 $launch"
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
