#!/bin/zsh
# Installa la bottega su questo Mac: skill, hook di Claude Code, promemoria delle 9 e delle 17.
# Si può rilanciare quando vuoi: rifà solo ciò che manca o è cambiato. I dati in dati/ non vengono mai toccati.
#
# Uso: ./installa.sh            installa o aggiorna
#      ./installa.sh --rimuovi  toglie skill, hook e promemoria (i dati restano)

set -e
radice=${0:A:h}
skills_dir=~/.claude/skills
settings=~/.claude/settings.json
agenti=~/Library/LaunchAgents
dominio=gui/$(id -u)

# Filtro jq che toglie da settings.json gli hook della bottega, con qualsiasi percorso.
togli_hook='
  def pulisci: map(.hooks |= map(select((.command // "") | test("/strumenti/hook_(registro|consumi)\\.sh\"?$") | not)))
               | map(select(.hooks | length > 0));
  if .hooks then
    .hooks |= (with_entries(.value |= pulisci) | with_entries(select(.value | length > 0)))
    | if .hooks == {} then del(.hooks) else . end
  else . end'

ok()   { print "  ✓ $1" }
nota() { print "  ! $1" }

# Applica un filtro jq a settings.json, tenendo una copia della versione precedente.
modifica_settings() {
  [[ -f $settings ]] || print '{}' > $settings
  jq "$@" $settings > $settings.tmp-bottega
  cp $settings $settings.bak-bottega
  mv $settings.tmp-bottega $settings
}

if [[ $1 == --rimuovi ]]; then
  print "Rimuovo la bottega"
  for s in $radice/skills/*(/); do
    t=$skills_dir/${s:t}
    if [[ -L $t && ${t:A} == ${s:A} ]]; then rm $t && ok "skill /${s:t} scollegata"; fi
  done
  if [[ -f $settings ]]; then
    modifica_settings $togli_hook && ok "hook tolti da settings.json (copia in settings.json.bak-bottega)"
  fi
  for p in $radice/launchd/*.plist; do
    launchctl bootout $dominio/${p:t:r} 2>/dev/null || true
    rm -f $agenti/${p:t} && ok "promemoria ${p:t:r} tolto"
  done
  print "Fatto. I dati in $radice/dati sono rimasti."
  exit 0
fi

print "Prerequisiti"
[[ $(uname) == Darwin ]] || { print "  ✗ serve macOS (i promemoria usano launchd e AppleScript)"; exit 1 }
for c in jq python3 osascript launchctl; do
  command -v $c >/dev/null && ok $c || { print "  ✗ manca $c"; exit 1 }
done
[[ -d /Applications/iTerm.app ]] && ok iTerm || nota "iTerm non trovato: /che-si-fa-oggi non potrà aprire le sessioni nelle tab"

print "Dati"
mkdir -p $radice/dati/archivio
[[ -f $radice/dati/lezioni.md ]] ||
  print '# Lezioni\n\nRegistro delle retrospettive di `/com-e-andata`, la più recente in fondo.' > $radice/dati/lezioni.md
[[ -f $radice/dati/da-approfondire.md ]] ||
  print '# Da approfondire\n\nArgomenti da studiare dopo la chiusura. Spunta quelli fatti, con una riga su cosa hai imparato.\n' > $radice/dati/da-approfondire.md
ok "cartella dati/ pronta"
[[ $radice == $HOME/Dev/bottega ]] || nota "le skill cercano i file in ~/Dev/bottega, ma la repo è in $radice: spostala lì"

print "Skill"
mkdir -p $skills_dir
for s in $radice/skills/*(/); do
  t=$skills_dir/${s:t}
  if [[ -L $t && ${t:A} == ${s:A} ]]; then ok "/${s:t}"
  elif [[ -e $t || -L $t ]]; then nota "/${s:t}: esiste già $t e non è un collegamento a questa repo, lo lascio com'è"
  else ln -s $s $t && ok "/${s:t} collegata"
  fi
done

print "Hook di Claude Code"
modifica_settings --arg r "\"$radice/strumenti/hook_registro.sh\"" --arg c "\"$radice/strumenti/hook_consumi.sh\"" "
  $togli_hook
  | .hooks.UserPromptSubmit += [{hooks: [{type: \"command\", command: \$r, timeout: 10}]}]
  | .hooks.Stop += [{hooks: [{type: \"command\", command: \$c, timeout: 30, async: true}]}]"
ok "UserPromptSubmit → registro dei lanci"
ok "Stop → token consumati (in background)"

print "Promemoria"
mkdir -p $agenti
for p in $radice/launchd/*.plist; do
  dest=$agenti/${p:t}
  nuovo=$(sed "s|__RADICE__|$radice|g" $p)
  if [[ -f $dest && $(<$dest) == $nuovo ]] && launchctl print $dominio/${p:t:r} >/dev/null 2>&1; then
    ok "${p:t:r} già attivo"
  else
    launchctl bootout $dominio/${p:t:r} 2>/dev/null || true
    print -r -- $nuovo > $dest
    launchctl bootstrap $dominio $dest && ok "${p:t:r} attivato"
  fi
done

print "\nBottega aperta. Le sessioni di Claude Code già avviate vedono gli hook dopo un riavvio (o aprendo /hooks)."
