"""Select native configuration and carry it into a separately launched terminal."""
from __future__ import annotations

import os
from pathlib import Path
import shlex
import shutil


def absolute(value):
    """Keep lexical symlinks/shims while fixing relative paths before chdir."""
    return Path(os.path.abspath(os.path.expanduser(str(value))))


def config_home(variable, default):
    value = os.environ.get(variable, str(default))
    if not value or '\0' in value:
        raise ValueError(f'{variable} must be a non-empty path without NUL')
    return absolute(value)


def claude_home():
    return config_home('CLAUDE_CONFIG_DIR', Path.home() / '.claude')


def codex_home():
    return config_home('CODEX_HOME', Path.home() / '.codex')


def executable(name):
    path = shutil.which(name)
    if path is None:
        raise ValueError(f'{name} CLI is unavailable; install it or choose another Provider explicitly.')
    return str(absolute(path))


def launch_command(argv, folder, root, launch_id=None, extra=None):
    """Initialize the selected home, then pin native paths before executing."""
    if launch_id is not None:
        import re
        if not re.fullmatch(r'[a-f0-9]{32}', launch_id):
            raise ValueError('Invalid Deskmate launch identity')
    values = {
        'HOME': str(absolute(Path.home())),
        'ZDOTDIR': str(config_home('ZDOTDIR', Path.home())),
        'PATH': os.pathsep.join(str(absolute(entry or os.curdir))
                              for entry in os.environ.get('PATH', os.defpath).split(os.pathsep)),
        'CODEX_HOME': str(codex_home()),
        'DESKMATE_DATA_DIR': str(config_home('DESKMATE_DATA_DIR', Path(root) / 'data')),
    }
    if 'CLAUDE_CONFIG_DIR' in os.environ:
        values['CLAUDE_CONFIG_DIR'] = str(claude_home())
    if launch_id is not None:
        values['DESKMATE_LAUNCH_ID'] = launch_id
    values.update(extra or {})
    assignments = [key + '=' + value for key, value in values.items()]
    unset = ['-u', 'CLAUDE_CONFIG_DIR', '-u', 'DESKMATE_LAUNCH_ID',
             '-u', 'CLAUDECODE', '-u', 'CLAUDE_CODE_ENTRYPOINT']
    native = ['/usr/bin/env', *unset, *assignments, *argv]
    shell = ('builtin cd -- ' + shlex.quote(str(absolute(folder))) +
             ' && builtin exec ' + shlex.join(native))
    if any('\0' in value for value in [*argv, shell, *assignments]):
        raise ValueError('Launch arguments must not contain NUL')
    # Unset absent optional configuration/correlation and nested-session markers
    # that might otherwise leak from the terminal application's environment.
    # Startup can supply the user's normal shell environment. Reapply only our
    # selected keys afterward so startup hooks cannot silently reroute the CLI.
    return shlex.join(['/usr/bin/env', *unset, *assignments, '/bin/zsh', '-l', '-i', '-c', shell])
