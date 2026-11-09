#!/usr/bin/env python3
"""Common setup/removal: stage native adapters, then publish recoverably."""
from __future__ import annotations

import argparse
import contextlib
import csv
import fcntl
import io
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import activity_log
import adapter_codex
import project_cards as cards
import providers
import reminders
from install_transaction import Transaction, file_state, recover, state

ROOT = Path(__file__).resolve().parents[1]
SHELL_BLOCK = '\n# >>> deskmate PATH >>>\nexport PATH="$HOME/.local/bin:$PATH"\n# <<< deskmate PATH <<<\n'
LABELS = ('com.deskmate.morning', 'com.deskmate.evening',
          'com.bottega.buongiorno', 'com.bottega.promemoria')


def run(args, **kwargs):
    result = subprocess.run(args, capture_output=True, text=True, timeout=15,
                            check=False, **kwargs)
    if result.returncode:
        raise ValueError(f'{Path(args[0]).name} failed ({result.returncode}): '
                         + (result.stderr or result.stdout).strip())
    return result.stdout


def available(args):
    detections = [providers.detect(provider) for provider in providers.PROVIDERS]
    for index, item in enumerate(detections):
        if item.provider.key == 'codex' and item.compatible:
            supported, warning = adapter_codex.hook_capability()
            if not supported:
                detections[index] = providers.Detection(item.provider, False, warning)
    print(providers.render(detections), end='')
    requested = set(args.provider or [])
    if requested:
        for item in detections:
            if item.provider.key in requested and not item.compatible:
                raise ValueError(f'Requested {item.provider.label} is unavailable: {item.reason}')
        detections = [item for item in detections if item.provider.key in requested]
    default, error = providers.choose_default(detections, args.default_provider,
                                               args.non_interactive or not sys.stdin.isatty())
    if error:
        raise ValueError(error + '; install a compatible Provider and rerun deskmate setup')
    return [item.provider.key for item in detections if item.compatible], default


def legacy_cards(projects):
    """Resolve lossy Claude folder keys from durable paths, never by decoding them."""
    explicit = {}
    for folder in projects:
        _, key, card, legacy = cards.identity(folder)
        explicit[legacy] = (key, card)
    result = []
    for legacy in sorted((Path.home() / '.claude/projects').glob('*/memory/project-card.md')):
        if legacy.is_symlink():
            target = legacy.resolve()
            if target.parent.parent != cards.data_root() / 'projects':
                raise ValueError(f'Unexpected Project card link: {legacy}')
            cards.read_card(target)
            if not target.is_file():
                raise ValueError(f'Dangling Project card link: {legacy}')
            continue
        text = legacy.read_bytes().decode('utf-8')
        cards.parse(text)
        if legacy in explicit:
            key, card = explicit[legacy]
        else:
            candidates = re.findall(r'\bfolder `([^`]+)`', text)
            index = legacy.parent.parent / 'sessions-index.json'
            if index.is_file():
                data = json.loads(index.read_text(encoding='utf-8'))
                if isinstance(data, dict):
                    candidates += [entry.get('projectPath') for entry in data.get('entries', [])
                                   if isinstance(entry, dict)]
                    candidates += [data.get('originalPath')]
            matches = {}
            for candidate in candidates:
                if not isinstance(candidate, str) or not Path(candidate).is_absolute():
                    continue
                try:
                    _, candidate_key, candidate_card, expected = cards.identity(candidate)
                except (OSError, ValueError):
                    continue
                if expected == legacy:
                    matches[candidate_key] = candidate_card
            if len(matches) != 1:
                raise ValueError(f'Cannot identify project for {legacy}; '
                                 'rerun deskmate setup --project /absolute/project/folder')
            key, card = next(iter(matches.items()))
        current, metadata = cards.read_card(card)
        if current is not None and cards.without_metadata(current) != cards.without_metadata(text):
            raise ValueError(f'Project card migration conflict: {legacy} and {card}')
        if current is None:
            checkpoints = re.findall(r'^Checkpoint[^\r\n]*', text, re.M)
            matched = re.search(r'\bsession `([^`]+)`', checkpoints[-1]) if checkpoints else None
            session = matched.group(1) if matched and matched.group(1).strip() else None
            metadata = dict(schema_version=1, revision=1,
                            provider='claude' if session else None, session_id=session)
            current = cards.render(text, metadata)
        result.append((legacy, card, current.encode('utf-8')))
    return result


def preflight(projects):
    config_path = cards.data_root() / 'config.json'
    config_state = state(config_path)
    config = providers.read_config()
    if state(config_path) != config_state:
        raise ValueError(f'Configuration changed while reading; retry setup: {config_path}')
    for path in sorted((cards.data_root() / 'projects').glob('*/project-card.md')):
        cards.read_card(path)
    fields, rows, old_log = activity_log.read_log(cards.data_root() / 'log.csv')
    migrations = legacy_cards(projects)
    return config, fields, rows, old_log, migrations, config_state


@contextlib.contextmanager
def installation_locks(data, new_cards=()):
    """Use the locks shared-card/log/native writers already honor."""
    with contextlib.ExitStack() as stack:
        lock_path = data.parent / ('.' + data.name + '.deskmate-setup.lock')
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = stack.enter_context(lock_path.open('a'))
        fcntl.flock(handle, fcntl.LOCK_EX)
        data.mkdir(parents=True, exist_ok=True)
        handle = stack.enter_context((data / '.log.lock').open('a'))
        fcntl.flock(handle, fcntl.LOCK_EX)
        directories = set((data / 'projects').glob('*')) | {path.parent for path in new_cards}
        for directory in sorted(directories):
            directory.mkdir(parents=True, exist_ok=True)
            if directory.is_dir():
                handle = stack.enter_context((directory / '.lock').open('a'))
                fcntl.flock(handle, fcntl.LOCK_EX)
        for directory in (Path.home() / '.claude', adapter_codex.codex_home()):
            directory.mkdir(parents=True, exist_ok=True)
            handle = stack.enter_context((directory / '.deskmate-integration.lock').open('a'))
            fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def native_paths(provider):
    if provider == 'claude':
        return Path.home() / '.claude/settings.json', Path.home() / '.claude/skills'
    return adapter_codex.hooks_path(), Path.home() / '.agents/skills'


def owned_link(path, target):
    return path.is_symlink() and path.resolve() == target.resolve()


@contextlib.contextmanager
def staged_environment(stage):
    values = {'HOME': str(stage), 'CODEX_HOME': str(stage / '.codex'),
              'DESKMATE_DATA_DIR': str(stage / 'data')}
    original = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for key, value in original.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def native_plan(transaction, stage, installed, remove=False):
    from adapter_cli import adapter, verify_logging
    guidance = []
    for provider in installed:
        settings, skills = native_paths(provider)
        sources = [p for p in sorted((ROOT / 'skills').iterdir()) if (p / 'SKILL.md').is_file()]
        for source in sources:
            target = skills / source.name
            owned = owned_link(target, source)
            if not remove and os.path.lexists(target) and not owned:
                raise ValueError(f'Existing skill is not owned by Deskmate: {target}; move or rename it')
            if remove:
                if owned:
                    transaction.add(target, {'kind': 'missing'})
            else:
                transaction.add(target, {'kind': 'link', 'target': str(source)})
        if remove and not settings.exists():
            continue
        original = state(settings)
        if original['kind'] == 'link':
            raise ValueError(f'Provider configuration must be a regular file: {settings}')
        stage_settings = stage / ('.claude/settings.json' if provider == 'claude' else '.codex/hooks.json')
        if settings.exists():
            stage_settings.parent.mkdir(parents=True, exist_ok=True)
            stage_settings.write_bytes(settings.read_bytes())
        with staged_environment(stage):
            implementation = adapter(provider)
            # Capability was checked against the real user configuration by available().
            # Staging constructs hooks without re-probing an empty synthetic Codex home.
            result = (implementation.configure_hooks(remove=remove, capability=(True, None))
                      if provider == 'codex' else implementation.configure_hooks(remove=remove))
            if not remove and result['status'] == 'ok':
                result['verification'] = verify_logging(provider)
        if result['status'] != 'ok':
            raise ValueError(f'{provider} integration: ' + '; '.join(result.get('warnings', [])))
        staged = state(stage_settings)
        if staged['kind'] == 'file' and original['kind'] == 'file':
            staged['mode'] = original['mode']
            if json.loads(staged['content']) == json.loads(original['content']):
                staged = original
        transaction.add(settings, staged, before=original)
        if not remove:
            guidance += [f'{provider}: logging verified (isolated synthetic hook; native approval pending)',
                         *result.get('guidance', []), *result.get('warnings', [])]
    return guidance


def shell_plan(transaction, remove=False):
    command = Path.home() / '.local/bin/deskmate'
    target = ROOT / 'bin/deskmate'
    if remove:
        if owned_link(command, target):
            transaction.add(command, {'kind': 'missing'})
    else:
        if os.path.lexists(command) and not owned_link(command, target):
            raise ValueError(f'Command path is not owned by Deskmate: {command}')
        transaction.add(command, {'kind': 'link', 'target': str(target)})
    shell = Path(os.environ.get('SHELL', '/bin/zsh')).name
    files = ('.bash_profile', '.bashrc') if shell == 'bash' else ('.zprofile', '.zshrc')
    for name in files:
        path = Path.home() / name
        original = state(path)
        if original['kind'] == 'link':
            if remove:
                continue
            raise ValueError(f'Shell configuration is a symlink: {path}; add ~/.local/bin to PATH manually')
        content = original.get('content', b'').decode('utf-8')
        changed = content.replace(SHELL_BLOCK, '') if remove else (
            content if SHELL_BLOCK in content or str(command.parent) in os.environ.get('PATH', '').split(os.pathsep)
            else content + SHELL_BLOCK)
        if changed != content:
            transaction.add(path, file_state(changed.encode(), original.get('mode', 0o600)))


def agent_owned(path):
    if not path.exists():
        return False
    value = plistlib.loads(path.read_bytes())
    argv = value.get('ProgramArguments', [])
    return bool(argv and Path(argv[0]).parent == ROOT / 'tools' and
                Path(argv[0]).name in ('morning_reminder.sh', 'evening_reminder.sh',
                                       'buongiorno.sh', 'promemoria.sh'))


def reminder_plan(transaction, config, stage, remove=False):
    actions = []
    r = {**reminders.DEFAULTS, **config.get('reminders', {})}
    errors = reminders.check(r)
    if errors and not remove:
        raise ValueError('Invalid reminder configuration: ' + '; '.join(errors))
    mac = not remove and 'mac' in r['channels']
    if mac and (sys.platform != 'darwin' or not shutil.which('launchctl') or not shutil.which('osascript')):
        raise ValueError('mac reminders require macOS, launchctl and osascript; '
                         'install prerequisites or remove mac from reminders.channels')
    environment = {**os.environ, 'DESKMATE_DATA_DIR': str(stage / 'data')}
    (stage / 'data').mkdir(exist_ok=True)
    (stage / 'data/config.json').write_text(json.dumps(config))
    for label in LABELS:
        path = Path.home() / 'Library/LaunchAgents' / (label + '.plist')
        owned = agent_owned(path)
        wanted = mac and label.startswith('com.deskmate.')
        if wanted and path.exists() and not owned:
            raise ValueError(f'Reminder is not owned by Deskmate: {path}')
        if not owned and not wanted:
            continue
        active = subprocess.run(['launchctl', 'print', f'gui/{os.getuid()}/{label}'],
                                capture_output=True, timeout=10, check=False).returncode == 0
        if wanted:
            kind = label.rsplit('.', 1)[-1]
            value = plistlib.loads(run([sys.executable, '-B', str(ROOT / 'bin/deskmate'),
                                       'reminders', 'plist', kind], env=environment).encode())
            value['EnvironmentVariables'] = {
                'HOME': str(Path.home()), 'DESKMATE_DATA_DIR': str(cards.data_root()),
                'PATH': str(Path(sys.executable).parent) + os.pathsep + os.environ.get('PATH', '/usr/bin:/bin')}
            candidate = file_state(plistlib.dumps(value))
            if state(path) != candidate or not active:
                actions.append((label, path, active, True))
            transaction.add(path, candidate)
        elif owned:
            transaction.add(path, {'kind': 'missing'})
            actions.append((label, path, active, False))
    if not remove and 'calendar' in r['channels']:
        old = cards.data_root() / 'deskmate-reminders.ics'
        if old.exists():
            (stage / 'data/deskmate-reminders.ics').write_bytes(old.read_bytes())
        result = run([sys.executable, '-B', str(ROOT / 'bin/deskmate'), 'reminders', 'ics'], env=environment)
        transaction.add(old, file_state((stage / 'data/deskmate-reminders.ics').read_bytes()))
        if result.strip() == 'changed':
            print(f'Calendar changed: import {old} into your calendar application.')
    return actions


def activate(actions):
    for label, path, active, wanted in actions:
        domain = f'gui/{os.getuid()}'
        if active:
            run(['launchctl', 'bootout', domain + '/' + label])
        if wanted:
            run(['launchctl', 'bootstrap', domain, str(path)])


def restore_agents(actions):
    errors = []
    for label, path, active, _ in actions:
        domain = f'gui/{os.getuid()}'
        try:
            subprocess.run(['launchctl', 'bootout', domain + '/' + label],
                           capture_output=True, timeout=10, check=False)
            # A failed bootout is harmless only when the service is actually absent.
            remaining = subprocess.run(['launchctl', 'print', domain + '/' + label],
                                       capture_output=True, timeout=10, check=False)
            if remaining.returncode == 0:
                raise ValueError(f'launchctl could not unload {label}')
            if active:
                run(['launchctl', 'bootstrap', domain, str(path)])
                if subprocess.run(['launchctl', 'print', domain + '/' + label],
                                  capture_output=True, timeout=10, check=False).returncode:
                    raise ValueError(f'launchctl could not restore {label}')
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            errors.append(str(error))
    return errors


def restore_transaction(metadata):
    actions = [(label, Path(path), active, wanted)
               for label, path, active, wanted in metadata.get('reminders', [])]
    errors = restore_agents(actions)
    if errors:
        raise ValueError('Reminder recovery needs attention; rerun after fixing launchctl: '
                         + '; '.join(errors))


def publish(transaction, actions, installed=()):
    from adapter_cli import verify_logging
    transaction.metadata = {'reminders': [(label, str(path), active, wanted)
                                         for label, path, active, wanted in actions]}
    transaction.apply()
    try:
        # Exercise the actual published hook definition; its event still goes to disposable data.
        for provider in installed:
            verify_logging(provider)
        activate(actions)
        transaction.commit()
    except BaseException:
        transaction.rollback(restore=restore_transaction)
        raise


def setup(args):
    initial = preflight(args.project)
    installed, default = available(args)
    data = cards.data_root()
    with installation_locks(data, [item[1] for item in initial[4]]):
        for backup in recover(data, restore=restore_transaction):
            print(f'Recovered interrupted installation: {backup}')
        config, fields, rows, old_log, migrations, original_config = preflight(args.project)
        config = dict(config, schema_version=1, providers={'installed': installed, 'default': default})
        config.setdefault('name', Path.home().name)
        config.setdefault('language', 'en')
        for field in ('name', 'language'):
            if getattr(args, field) is not None:
                config[field] = getattr(args, field)
        config['reminders'] = {**reminders.DEFAULTS, **config.get('reminders', {})}
        transaction = Transaction(data)
        configured = file_state((json.dumps(config, indent=2, sort_keys=True) + '\n').encode(),
                                original_config.get('mode', 0o600))
        if original_config['kind'] == 'file' and json.loads(original_config['content']) == config:
            configured = original_config
        transaction.add(data / 'config.json', configured, before=original_config)
        if old_log:
            output = io.StringIO(newline='')
            writer = csv.DictWriter(output, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
            transaction.add(data / 'log.csv', file_state(output.getvalue().encode(),
                                                        (data / 'log.csv').stat().st_mode & 0o777))
        for legacy, shared, text in migrations:
            transaction.add(shared, file_state(text))
            transaction.add(legacy, {'kind': 'link', 'target': str(shared)})
        for name, content in [('lessons.md', '# Lessons\n\nRetrospectives, latest at the bottom.\n'),
                              ('study-later.md', '# Study later\n\nTopics to study after closing time.\n')]:
            if not (data / name).exists():
                transaction.add(data / name, file_state(content.encode()))
        with tempfile.TemporaryDirectory(prefix='deskmate-setup-stage-') as directory:
            stage = Path(directory)
            guidance = native_plan(transaction, stage, installed)
            native_plan(transaction, stage, [p for p in ('claude', 'codex') if p not in installed], remove=True)
            shell_plan(transaction)
            actions = reminder_plan(transaction, config, stage)
            publish(transaction, actions, installed)
        for entry in transaction.entries:
            print(f'Updated: {entry["path"]}')
        if transaction.directory:
            print(f'Migration backups and recovery journal: {transaction.directory}')
        print('\n'.join(guidance))
        print('Deskmate ready: ~/.local/bin/deskmate. Open a new shell or run export PATH="$HOME/.local/bin:$PATH".')


def remove(args):
    data = cards.data_root()
    purge = args.purge_data
    interactive = not args.non_interactive and sys.stdin.isatty()
    if interactive:
        if not purge:
            purge = input('Purge personal data? [y/N] ').strip().lower() == 'y'
        if purge and input('Type DELETE to permanently purge personal data: ') != 'DELETE':
            raise ValueError('Data purge cancelled: exact confirmation DELETE is required')
    protected = (Path.home(), ROOT, Path.home() / '.claude', Path.home() / '.agents',
                 adapter_codex.codex_home().resolve(), Path.home() / 'Library/LaunchAgents',
                 Path.home() / '.local/bin')
    if purge and any(data == path or data in path.parents for path in protected):
        raise ValueError(f'Refusing unsafe data purge root: {data}')
    with installation_locks(data):
        for backup in recover(data, restore=restore_transaction):
            print(f'Recovered interrupted installation: {backup}')
        transaction = Transaction(data)
        with tempfile.TemporaryDirectory(prefix='deskmate-remove-stage-') as directory:
            stage = Path(directory)
            native_plan(transaction, stage, ['claude', 'codex'], remove=True)
            shell_plan(transaction, remove=True)
            actions = reminder_plan(transaction, {}, stage, remove=True)
            publish(transaction, actions)
        if purge:
            for legacy in (Path.home() / '.claude/projects').glob('*/memory/project-card.md'):
                if legacy.is_symlink() and legacy.resolve().parent.parent == data / 'projects':
                    legacy.unlink()
            shutil.rmtree(data)
            print(f'Deskmate integrations removed; personal data purged: {data}')
        else:
            print(f'Deskmate integrations removed; personal data preserved: {data}')


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest='command', required=True)
    install = commands.add_parser('setup')
    install.add_argument('--provider', choices=['claude', 'codex'], action='append')
    install.add_argument('--default-provider', choices=['claude', 'codex'])
    install.add_argument('--project', action='append', default=[])
    install.add_argument('--name')
    install.add_argument('--language')
    uninstall = commands.add_parser('remove')
    uninstall.add_argument('--purge-data', action='store_true')
    for command in (install, uninstall):
        command.add_argument('--non-interactive', action='store_true')
    args = parser.parse_args()
    try:
        (setup if args.command == 'setup' else remove)(args)
        return 0
    except (OSError, ValueError, TypeError, KeyError, csv.Error, EOFError, subprocess.SubprocessError) as error:
        print(f'deskmate {args.command}: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
