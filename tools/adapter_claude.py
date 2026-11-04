"""Claude Code's native storage and integration behind the Provider contract."""

from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import os
import shlex
import subprocess
import tempfile
import copy
import fcntl


ROOT = pathlib.Path(__file__).resolve().parent.parent


def projects() -> pathlib.Path:
    return pathlib.Path.home() / '.claude' / 'projects'


def timestamp(value):
    try:
        parsed = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed.replace(tzinfo=parsed.tzinfo or dt.timezone.utc).timestamp()
    except (AttributeError, TypeError, ValueError):
        return None


def discover(since: str) -> list[dict]:
    """Use indexes and file metadata only; never open conversation transcripts."""
    threshold = dt.datetime.combine(dt.date.fromisoformat(since), dt.time()).timestamp()
    records = {}
    indexed = set()
    for index in sorted(projects().glob('*/sessions-index.json')):
        try:
            data = json.loads(index.read_text(encoding='utf-8'))
            entries = data.get('entries', []) if isinstance(data, dict) else []
            if not isinstance(entries, list):
                continue
        except (OSError, UnicodeError, ValueError):
            continue
        for entry in entries:
            if not isinstance(entry, dict) or entry.get('isSidechain'):
                continue
            session = entry.get('sessionId')
            end = entry.get('modified')
            if not isinstance(session, str) or not session or timestamp(end) is None:
                continue
            indexed.add(session)
            if timestamp(end) < threshold:
                continue
            cwd = entry.get('projectPath')
            start = entry.get('created')
            warnings = []
            if not isinstance(cwd, str) or timestamp(start) is None:
                warnings.append('Malformed session index metadata omitted.')
                cwd = cwd if isinstance(cwd, str) else None
                start = start if timestamp(start) is not None else None
            records[session] = {'provider': 'claude', 'id': session,
                                'cwd': cwd, 'start': start,
                                'end': end, 'usage': {}, 'status': 'degraded' if warnings else 'ok',
                                'warnings': warnings}
    for path in sorted(projects().glob('*/*.jsonl')):
        if path.stem in indexed or not path.is_file():
            continue
        try:
            modified = path.stat().st_mtime
        except OSError:
            continue
        if modified >= threshold:
            end = dt.datetime.fromtimestamp(modified, dt.timezone.utc).isoformat()
            records[path.stem] = {'provider': 'claude', 'id': path.stem,
                                  'cwd': None, 'start': None, 'end': end, 'usage': {},
                                  'status': 'degraded', 'warnings': [
                                      'Session index unavailable; transcript metadata not read.']}
    return sorted(records.values(), key=lambda item: item['end'])


def read_session(session_id: str) -> dict:
    return _read_transcript(session_id, include_messages=True)


def read_usage(session_id: str) -> dict:
    """Scan native counters; never access or construct conversation content."""
    return _read_transcript(session_id, include_messages=False)


def _read_transcript(session_id: str, *, include_messages: bool) -> dict:
    session = {'provider': 'claude', 'id': session_id, 'cwd': None,
               'start': None, 'end': None, 'usage': {},
               'status': 'ok', 'warnings': []}
    if include_messages:
        session['messages'] = []

    def warn(message):
        session['status'] = 'degraded'
        if message not in session['warnings']:
            session['warnings'].append(message)

    # Native IDs are filenames, never paths or glob expressions.
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', session_id):
        warn('Invalid Claude session ID.')
        return session
    paths = list(projects().glob(f'*/{session_id}.jsonl'))
    if len(paths) != 1:
        warn('Claude transcript unavailable or ambiguous.')
        return session
    seen = set()
    try:
        with paths[0].open(encoding='utf-8', errors='strict') as handle:
            for line in handle:
                try:
                    row = json.loads(line)
                except ValueError:
                    warn('Malformed transcript records were omitted.')
                    continue
                if not isinstance(row, dict):
                    warn('Malformed transcript records were omitted.')
                    continue
                if row.get('isSidechain') or row.get('isMeta'):
                    continue
                role = row.get('type')
                if role not in ('user', 'assistant'):
                    continue
                message = row.get('message')
                if not isinstance(message, dict):
                    warn('Malformed transcript records were omitted.')
                    continue
                cwd = row.get('cwd')
                if isinstance(cwd, str) and not session['cwd']:
                    session['cwd'] = cwd
                ts = row.get('timestamp')
                if timestamp(ts) is not None:
                    session['start'] = session['start'] or ts
                    session['end'] = ts
                elif ts is not None:
                    warn('Invalid transcript timestamp omitted.')
                    ts = None
                usage = message.get('usage')
                identity = message.get('id')
                if isinstance(usage, dict) and role == 'assistant':
                    if not isinstance(identity, str) or identity not in seen:
                        if isinstance(identity, str):
                            seen.add(identity)
                        session['usage']['turns'] = session['usage'].get('turns', 0) + 1
                        for key, value in usage.items():
                            if key in ('input_tokens', 'cache_creation_input_tokens',
                                       'cache_read_input_tokens', 'output_tokens') and type(value) is int and value >= 0:
                                session['usage'][key] = session['usage'].get(key, 0) + value
                if not include_messages:
                    continue
                content = message.get('content')
                if isinstance(content, list):
                    content = '\n'.join(block['text'] for block in content
                                        if isinstance(block, dict) and block.get('type') == 'text'
                                        and isinstance(block.get('text'), str))
                if not isinstance(content, str) or not content.strip():
                    continue
                if role == 'user' and content.lstrip().startswith('<'):
                    name = re.search(r'<command-name>(.*?)</command-name>', content, re.S)
                    if name is None:
                        continue
                    args = re.search(r'<command-args>(.*?)</command-args>', content, re.S)
                    content = (name.group(1) + ' ' + (args.group(1) if args else '')).strip()
                session['messages'].append({'role': role, 'timestamp': ts, 'text': content.strip()})
    except (OSError, UnicodeError) as error:
        warn(f'Claude transcript unreadable: {error.reason if isinstance(error, UnicodeError) else error.strerror}.')
    return session


def resume_available(session_id: str, folder: str | None = None) -> bool:
    """Read native identity metadata only, independently of transcript analytics."""
    if not isinstance(session_id, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', session_id):
        return False
    matches = []
    for index in projects().glob('*/sessions-index.json'):
        try:
            data = json.loads(index.read_text(encoding='utf-8'))
            entries = data.get('entries', []) if isinstance(data, dict) else []
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict) or entry.get('isSidechain') or entry.get('sessionId') != session_id:
                    continue
                cwd = entry.get('projectPath')
                if not isinstance(cwd, str) or not pathlib.Path(cwd).is_absolute():
                    return False
                if not (index.parent / (session_id + '.jsonl')).is_file():
                    return False
                matches.append(pathlib.Path(cwd).resolve())
        except (OSError, UnicodeError, ValueError):
            continue
    if matches:
        return len(matches) == 1 and (folder is None or matches[0] == pathlib.Path(folder).resolve())
    # Native folder-key encoding is lossy (a-b and a_b can share a key).
    # Without trusted index metadata, filenames cannot prove project identity.
    return False


def launch(folder: str, session_id: str | None = None, prompt: str | None = None,
           dry_run: bool = False, title: str | None = None,
           launch_id: str | None = None) -> dict:
    folder = str(pathlib.Path(folder).expanduser().resolve())
    argv = ['claude', '--resume', session_id] if session_id else ['claude']
    if prompt is not None:
        argv += ['--', prompt]
    result = {'provider': 'claude', 'mode': 'resume' if session_id else 'new',
              'argv': argv, 'cwd': folder, 'session_id': session_id,
              'status': 'ok', 'warnings': []}
    terminal_submission = False
    try:
        if not pathlib.Path(folder).is_dir():
            raise ValueError('Project folder does not exist.')
        if session_id is not None and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', session_id):
            raise ValueError('Invalid Claude session ID.')
        title = title or pathlib.Path(folder).name
        if any(ord(character) < 32 or ord(character) == 127 for character in title):
            raise ValueError('Terminal title must not contain control characters.')
        if any('\0' in argument for argument in argv):
            raise ValueError('Launch arguments must not contain NUL.')
        context = []
        if launch_id is not None:
            if not re.fullmatch(r'[a-f0-9]{32}', launch_id):
                raise ValueError('Invalid Deskmate launch identity')
            context = ['/usr/bin/env', 'DESKMATE_LAUNCH_ID=' + launch_id,
                       'DESKMATE_DATA_DIR=' + str(pathlib.Path(os.environ.get(
                           'DESKMATE_DATA_DIR', ROOT / 'data')).expanduser().resolve())]
            if 'CODEX_HOME' in os.environ:
                context.append('CODEX_HOME=' + str(pathlib.Path(os.environ['CODEX_HOME']).expanduser().resolve()))
        if dry_run or os.environ.get('DESKMATE_DRY_RUN'):
            return result
        if session_id:
            processes = subprocess.run(['ps', '-axo', 'pid=,tty=,command='],
                                       capture_output=True, text=True, timeout=5, check=True)
            for line in processes.stdout.splitlines():
                parts = line.strip().split(None, 2)
                if len(parts) != 3:
                    continue
                try:
                    native = shlex.split(parts[2])
                except ValueError:
                    continue
                if not native or pathlib.Path(native[0]).name != 'claude':
                    continue
                if not any(native[index:index + 2] in (['--resume', session_id], ['-r', session_id])
                           for index in range(len(native) - 1)):
                    continue
                focused = subprocess.run(['osascript', '-', '/dev/' + parts[1]], input='''on run argv
tell application "iTerm"
repeat with w in windows
repeat with t in tabs of w
repeat with s in sessions of t
if tty of s is (item 1 of argv) then
select w
tell t to select
activate
return "focused"
end if
end repeat
end repeat
end repeat
end tell
return "unavailable"
end run
''', capture_output=True, text=True, timeout=10, check=True)
                if focused.stdout.strip() != 'focused':
                    raise ValueError('Claude session is already running outside a reachable iTerm tab; close it before resuming.')
                result['focused'] = True
                result['warnings'].append('Existing Work session tab brought to front.')
                return result
        command = ("printf '\\033]0;%s\\007' " + shlex.quote(title) + '; cd ' +
                   shlex.quote(folder) + ' && CLAUDE_CODE_DISABLE_TERMINAL_TITLE=1 ' +
                   shlex.join([*context, *argv]))
        terminal_submission = True
        subprocess.run(['osascript', '-', command], input='''on run argv
tell application "iTerm"
activate
if (count of windows) = 0 then create window with default profile
tell current window
set t to (create tab with default profile)
tell current session of t to write text (item 1 of argv)
end tell
end tell
end run
''', capture_output=True, text=True, timeout=10, check=True)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        result['status'] = 'error'
        result['submission_uncertain'] = terminal_submission and isinstance(error, subprocess.SubprocessError)
        result['warnings'].append(f'Claude launch failed: {error}')
    return result


def hook_argv():
    return [str(ROOT / 'bin/deskmate'), 'hook-event', '--provider', 'claude']


def hooks_path():
    return pathlib.Path.home() / '.claude/settings.json'


def verification_hook(session_id, cwd):
    """Resolve the installed native prompt hook and its verification payload."""
    settings = json.loads(hooks_path().read_text(encoding='utf-8'))
    for entry in settings.get('hooks', {}).get('UserPromptSubmit', []):
        for hook in entry.get('hooks', []):
            if owns_hook(hook) and shlex.split(hook['command']) == hook_argv():
                return hook_argv(), {'hook_event_name': 'UserPromptSubmit',
                                     'session_id': session_id, 'cwd': cwd,
                                     'prompt': '/checkpoint integration verification'}
    raise ValueError('Deskmate UserPromptSubmit hook is not installed.')


def owns_hook(hook):
    if not isinstance(hook, dict) or hook.get('type') != 'command':
        return False
    try:
        command = shlex.split(hook.get('command', ''))
    except (TypeError, ValueError):
        return False
    if command and pathlib.Path(command[0]).is_absolute():
        command[0] = str(pathlib.Path(command[0]).resolve())
    return command in (hook_argv(),
                       [str(ROOT / 'tools/hook_log.sh')],
                       [str(ROOT / 'tools/hook_tokens.sh')])


def configure_hooks(remove: bool = False) -> dict:
    result = {'provider': 'claude', 'status': 'ok', 'warnings': [],
              'guidance': ['Claude discovers shared skills with native /skill syntax.',
                           'Review normal project trust and hook approvals. Native lifecycle hooks confirm Work session ownership; unconfirmed launches stay pending.']}
    settings = hooks_path()
    temporary = None
    try:
        settings.parent.mkdir(parents=True, exist_ok=True)
        with (settings.parent / '.deskmate-integration.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            data = json.loads(settings.read_text(encoding='utf-8')) if settings.exists() else {}
            if not isinstance(data, dict) or not isinstance(data.get('hooks', {}), dict):
                raise ValueError('Claude settings and hooks must be JSON objects.')
            data = copy.deepcopy(data)
            hooks = data.setdefault('hooks', {})
            for event, entries in list(hooks.items()):
                if not isinstance(entries, list):
                    raise ValueError(f'Claude {event} hooks must be a list.')
                retained = []
                for entry in entries:
                    if not isinstance(entry, dict) or not isinstance(entry.get('hooks'), list):
                        raise ValueError(f'Invalid Claude {event} hook entry.')
                    remaining = [hook for hook in entry['hooks'] if not owns_hook(hook)]
                    if len(remaining) == len(entry['hooks']):
                        retained.append(entry)
                    elif remaining:
                        retained.append({**entry, 'hooks': remaining})
                if retained or not entries:
                    hooks[event] = retained
                else:
                    hooks.pop(event)
            if not remove:
                command = shlex.join(hook_argv())
                for event in ['SessionStart', 'SessionEnd', 'UserPromptSubmit', 'PreToolUse', 'Stop']:
                    hook = {'type': 'command', 'command': command, 'timeout': 30 if event == 'Stop' else 10}
                    if event == 'Stop':
                        hook['async'] = True
                    entry = {'hooks': [hook]}
                    if event == 'PreToolUse':
                        entry['matcher'] = 'Skill'
                    hooks.setdefault(event, []).append(entry)
            skills = [(source, pathlib.Path.home() / '.claude/skills' / source.name)
                      for source in sorted((ROOT / 'skills').iterdir())
                      if source.is_dir() and (source / 'SKILL.md').is_file()]
            for source, target in skills:
                if target.exists() or target.is_symlink():
                    if not target.is_symlink() or target.resolve() != source.resolve():
                        if remove:
                            continue
                        raise ValueError(f'Existing skill is not owned by Deskmate: {target.name}')
            for source, target in skills:
                if remove:
                    if target.is_symlink() and target.resolve() == source.resolve():
                        target.unlink()
                elif not target.is_symlink():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.symlink_to(source, target_is_directory=True)
            with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=settings.parent,
                                             prefix='.deskmate-settings-', delete=False) as handle:
                temporary = pathlib.Path(handle.name)
                json.dump(data, handle, indent=2, sort_keys=True)
                handle.write('\n')
            if settings.exists():
                temporary.chmod(settings.stat().st_mode & 0o777)
            os.replace(temporary, settings)
    except (OSError, ValueError, UnicodeError) as error:
        result['status'] = 'error'
        result['warnings'].append(f'Claude integration failed: {error}')
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return result
