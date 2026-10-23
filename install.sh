#!/bin/zsh
# Installs deskmate on this Mac: skills, Claude Code hooks, morning and evening reminders.
# Preferences (name, language, reminders) live in data/config.json; this script applies them.
# Safe to run again at any time: it only redoes what is missing or changed. Files in data/ are never overwritten.
#
# Usage: ./install.sh [--name <name>] [--language <en|it>]   install or update
#        ./install.sh --remove                                 remove skills, hooks and reminders (data stays)

set -e
root=${0:A:h}
skills_dir=~/.claude/skills
settings=~/.claude/settings.json
agents=~/Library/LaunchAgents
domain=gui/$(id -u)
config=$root/data/config.json

# jq filter that removes the deskmate hooks from settings.json, whatever their path
# (it also matches the names used by older versions).
remove_hooks='
  def clean: map(.hooks |= map(select((.command // "") | test("/(tools|strumenti)/hook_(log|tokens|registro|consumi)\\.sh\"?$") | not)))
             | map(select(.hooks | length > 0));
  if .hooks then
    .hooks |= (with_entries(.value |= clean) | with_entries(select(.value | length > 0)))
    | if .hooks == {} then del(.hooks) else . end
  else . end'

ok()   { print "  ✓ $1" }
warn() { print "  ! $1" }

# Applies a jq filter to settings.json, keeping a copy of the previous version.
edit_settings() {
  [[ -f $settings ]] || print '{}' > $settings
  jq "$@" $settings > $settings.tmp-deskmate
  cp $settings $settings.bak-deskmate
  mv $settings.tmp-deskmate $settings
}

# Unloads and deletes the LaunchAgents of this and older versions.
remove_agents() {
  for label in com.deskmate.morning com.deskmate.evening com.bottega.buongiorno com.bottega.promemoria; do
    if [[ -f $agents/$label.plist ]] || launchctl print $domain/$label >/dev/null 2>&1; then
      launchctl bootout $domain/$label 2>/dev/null || true
      rm -f $agents/$label.plist
      ok "reminder $label removed"
    fi
  done
}

name="" language=""
while (( $# )); do
  case $1 in
    --remove) remove=1 ;;
    --name) name=$2; shift ;;
    --language) language=$2; shift ;;
    *) print "Unknown option: $1"; exit 1 ;;
  esac
  shift
done

if [[ -n $remove ]]; then
  print "Removing deskmate"
  for s in $root/skills/*(/); do
    t=$skills_dir/${s:t}
    if [[ -L $t && ${t:A} == ${s:A} ]]; then rm $t && ok "skill /${s:t} unlinked"; fi
  done
  if [[ -f $settings ]]; then
    edit_settings $remove_hooks && ok "hooks removed from settings.json (copy in settings.json.bak-deskmate)"
  fi
  remove_agents
  print "Done. The data in $root/data is still there."
  exit 0
fi

print "Prerequisites"
[[ $(uname) == Darwin ]] || { print "  ✗ macOS is required (the reminders use launchd and AppleScript)"; exit 1 }
for c in jq python3 osascript launchctl; do
  command -v $c >/dev/null && ok $c || { print "  ✗ $c is missing"; exit 1 }
done
[[ -d /Applications/iTerm.app ]] && ok iTerm || warn "iTerm not found: /whats-on-today won't be able to open sessions in tabs"
[[ $root == $HOME/Dev/mc_dev/deskmate ]] || warn "the skills look for files in ~/Dev/mc_dev/deskmate, but the repo is in $root: move it there"

print "Data"
mkdir -p $root/data/archive
[[ -f $root/data/lessons.md ]] ||
  print '# Lessons\n\nLog of the `/how-did-it-go` retrospectives, latest at the bottom.' > $root/data/lessons.md
[[ -f $root/data/study-later.md ]] ||
  print '# Study later\n\nTopics to study after closing time. Tick them off with one line on what you learned.\n' > $root/data/study-later.md
if [[ -n $name || -n $language || ! -f $config ]]; then
  [[ -f $config ]] || print '{}' > $config
  default_name=${$(id -F)%% *}
  jq --arg n "$name" --arg l "$language" --arg dn "$default_name" \
    '.name = (if $n != "" then $n else (.name // $dn) end) | .language = (if $l != "" then $l else (.language // "en") end)' \
    $config > $config.tmp && mv $config.tmp $config
fi
jq '.reminders = ({morning: "09:00", evening: "17:00", days: ["mon","tue","wed","thu","fri"], channels: ["mac"]} + (.reminders // {}))' \
  $config > $config.tmp && mv $config.tmp $config
problems=$(python3 -I $root/tools/reminders.py check) || { print "  ✗ data/config.json:\n$problems" | sed '2,$s/^/      /'; exit 1 }
ok "data/ ready, name: $(jq -r .name $config), language: $(jq -r .language $config)"

print "Skills"
mkdir -p $skills_dir
for s in $root/skills/*(/); do
  t=$skills_dir/${s:t}
  if [[ -L $t && ${t:A} == ${s:A} ]]; then ok "/${s:t}"
  elif [[ -e $t || -L $t ]]; then warn "/${s:t}: $t already exists and is not a link to this repo, leaving it alone"
  else ln -s $s $t && ok "/${s:t} linked"
  fi
done

print "Claude Code hooks"
edit_settings --arg l "\"$root/tools/hook_log.sh\"" --arg t "\"$root/tools/hook_tokens.sh\"" "
  $remove_hooks
  | .hooks.UserPromptSubmit += [{hooks: [{type: \"command\", command: \$l, timeout: 10}]}]
  | .hooks.Stop += [{hooks: [{type: \"command\", command: \$t, timeout: 30, async: true}]}]"
ok "UserPromptSubmit → log of skill runs"
ok "Stop → tokens used (in the background)"

print "Reminders: $(jq -r '.reminders | "\(.morning) and \(.evening), \(.days | join(" ")), via \(.channels | join(" + "))"' $config)"
channels=$(jq -r '.reminders.channels | join(" ")' $config)
mkdir -p $agents
if [[ " $channels " == *" mac "* ]]; then
  for label in com.bottega.buongiorno com.bottega.promemoria; do
    if [[ -f $agents/$label.plist ]]; then
      launchctl bootout $domain/$label 2>/dev/null || true
      rm -f $agents/$label.plist && ok "old reminder $label removed"
    fi
  done
  for kind in morning evening; do
    label=com.deskmate.$kind dest=$agents/com.deskmate.$kind.plist
    new=$(python3 -I $root/tools/reminders.py plist $kind)
    if [[ -f $dest && $(<$dest) == $new ]] && launchctl print $domain/$label >/dev/null 2>&1; then
      ok "mac: $kind alert already active"
    else
      launchctl bootout $domain/$label 2>/dev/null || true
      print -r -- $new > $dest
      launchctl bootstrap $domain $dest && ok "mac: $kind alert active"
    fi
  done
else
  remove_agents
  ok "mac: alerts off"
fi
if [[ " $channels " == *" calendar "* ]]; then
  if [[ $(python3 -I $root/tools/reminders.py ics) == changed ]]; then
    warn "calendar: new events in data/deskmate-reminders.ics, open it to import them (open data/deskmate-reminders.ics)"
  else
    ok "calendar: events unchanged"
  fi
fi
[[ " $channels " == *" slack "* ]] && warn "slack: not available yet, see ROADMAP.md"

print "\nDeskmate is ready. Claude Code sessions already running see the hooks after a restart (or after opening /hooks)."
