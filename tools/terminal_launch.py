"""Private iTerm launch payloads and bounded native-process verification."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import provider_environment

START_TIMEOUT = 10.0
POLL_INTERVAL = 0.1
SCRIPT = '''on run argv
tell application "iTerm"
    if (count of windows) is 0 then
        set w to (create window with default profile command (item 1 of argv))
        set s to current session of w
    else
        tell current window
            set t to (create tab with default profile command (item 1 of argv))
            set s to current session of t
        end tell
    end if
    set name of s to item 2 of argv
    activate
    return (tty of s) & (ASCII character 9) & (unique ID of s)
end tell
end run
'''


class LaunchError(ValueError):
    def __init__(self, message, *, uncertain=False, tty=None, terminal_session_id=None):
        super().__init__(message)
        self.uncertain = uncertain
        self.details = {key: value for key, value in (
            ('tty', tty), ('terminal_session_id', terminal_session_id)) if value is not None}


def _private_payload(argv, provider, folder):
    directory = Path(tempfile.mkdtemp(prefix='deskmate-launch-')).resolve()
    directory.chmod(0o700)
    path = directory / 'payload.json'
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            json.dump({'schema_version': 1, 'provider': provider,
                       'cwd': str(folder), 'argv': argv}, stream)
        return path
    except BaseException:
        shutil.rmtree(directory)
        raise


def _script_process(pid, command, executable, timeout):
    """A selected script's interpreter is also a valid native CLI process."""
    try:
        with executable.open('rb') as stream:
            first = stream.readline(1024)
        if not first.startswith(b'#!'):
            return False
        interpreter = shlex.split(first[2:].decode().strip())
        if not interpreter:
            return False
        if Path(interpreter[0]).name == 'env':
            interpreter = interpreter[1:]
            if interpreter[:1] == ['-S']:
                interpreter = interpreter[1:]
        if not interpreter or interpreter[0].startswith('-'):
            return False
        expected, options = interpreter[0], interpreter[1:]
        location = expected if Path(expected).is_absolute() else shutil.which(expected)
        if location is None:
            return False
        resolved = Path(location).resolve()
        if Path(command).is_absolute():
            matches = Path(command).resolve() == resolved
        else:
            matches = command in (Path(expected).name, resolved.name)
        if not matches:
            return False
        result = subprocess.run(['ps', '-p', str(pid), '-o', 'args='],
                                capture_output=True, text=True, timeout=timeout, check=False)
        if result.returncode:
            return False
        args = result.stdout.strip()
        for prefix in (command, Path(command).name, expected, str(resolved)):
            for path in (str(executable), str(executable.resolve())):
                candidate = ' '.join([prefix, *options, path])
                if args == candidate or args.startswith(candidate + ' '):
                    return True
    except (OSError, ValueError, UnicodeError, subprocess.SubprocessError):
        pass
    return False


def wait_for_process(executable, tty, *, timeout=START_TIMEOUT):
    executable = Path(executable)
    resolved = executable.resolve()
    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None
        try:
            result = subprocess.run(['ps', '-t', tty.removeprefix('/dev/'), '-o', 'pid=,comm='],
                                    capture_output=True, text=True, timeout=min(1.0, remaining), check=False)
        except subprocess.TimeoutExpired:
            if time.monotonic() >= deadline:
                return None
            raise
        if result.returncode:
            raise LaunchError('Cannot inspect processes in iTerm ' + tty + '; check process permissions.',
                              uncertain=True, tty=tty)
        for row in result.stdout.splitlines():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            parts = row.strip().split(None, 1)
            if len(parts) != 2 or not parts[0].isdigit() or int(parts[0]) <= 0:
                continue
            pid, command = int(parts[0]), parts[1]
            named = command in (executable.name, resolved.name)
            exact = Path(command).is_absolute() and Path(command).resolve() in (executable, resolved)
            if named or exact or _script_process(pid, command, executable, min(1.0, remaining)):
                return pid
        time.sleep(min(POLL_INTERVAL, max(0.0, deadline - time.monotonic())))


def start(argv, provider, folder, root, title, launch_id=None, extra=None):
    # Validate the selected environment before creating private storage.
    try:
        provider_environment.launch_command(argv, folder, root, launch_id, extra)
        path = _private_payload(argv, provider, folder)
    except (OSError, ValueError) as error:
        raise LaunchError('Cannot prepare the native launch: ' + str(error)) from None
    submitted = False
    tty = terminal_id = None
    try:
        helper = [sys.executable, '-I', str(Path(__file__).resolve()), '--payload', str(path)]
        command = provider_environment.launch_command(helper, folder, root, launch_id, extra)
        try:
            result = subprocess.run(['osascript', '-', command, title], input=SCRIPT,
                                    capture_output=True, text=True, timeout=10, check=False)
        except subprocess.TimeoutExpired:
            submitted = True
            raise
        submitted = True
        if result.returncode:
            raise LaunchError('iTerm launch failed; inspect the terminal and Automation permission.', uncertain=True)
        fields = result.stdout.strip().split('\t')
        if (len(fields) != 2 or not fields[0].startswith('/dev/tty')
                or not fields[0][8:].isalnum() or not fields[1]
                or any(ord(c) < 32 for c in fields[1])):
            raise LaunchError('iTerm did not return a valid tab and tty; inspect the terminal before retrying.', uncertain=True)
        tty, terminal_id = fields
        pid = wait_for_process(argv[0], tty)
        if pid is None:
            raise LaunchError(f'No {provider} process appeared on {tty} within {START_TIMEOUT:g} seconds. '
                              f'Inspect iTerm tab {terminal_id}; do not retry until that tab is checked.',
                              uncertain=True, tty=tty, terminal_session_id=terminal_id)
        # The runner leaves early failures open for inspection until acknowledged.
        # A very fast process may already have exited after ps observed it.
        try:
            descriptor = os.open(path.with_name('started'), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, 'w') as stream:
                stream.write(str(pid))
        except FileNotFoundError:
            pass
        return {'tty': tty, 'pid': pid, 'terminal_session_id': terminal_id}
    except LaunchError as error:
        if tty is not None:
            error.details.setdefault('tty', tty)
            error.details.setdefault('terminal_session_id', terminal_id)
        path.unlink(missing_ok=True)
        # A runner still displaying failure information owns its directory.
        try:
            path.parent.rmdir()
        except OSError:
            pass
        raise
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        path.unlink(missing_ok=True)
        try:
            path.parent.rmdir()
        except OSError:
            pass
        context = (f' Inspect iTerm tab {terminal_id} on {tty}.' if tty is not None else '')
        raise LaunchError(f'Native {provider} launch could not be verified: ' + str(error) + context, uncertain=submitted,
                          tty=tty, terminal_session_id=terminal_id) from None
    except BaseException:
        path.unlink(missing_ok=True)
        try:
            path.parent.rmdir()
        except OSError:
            pass
        raise


def _read_payload(path):
    directory = path.parent
    parent = directory.lstat()
    value = path.lstat()
    if (path.name != 'payload.json' or not directory.name.startswith('deskmate-launch-')
            or not stat.S_ISDIR(parent.st_mode) or parent.st_uid != os.getuid()
            or stat.S_IMODE(parent.st_mode) != 0o700
            or not stat.S_ISREG(value.st_mode) or value.st_uid != os.getuid()
            or stat.S_IMODE(value.st_mode) != 0o600 or value.st_nlink != 1):
        raise ValueError('Launch payload must be a private owned regular file')
    descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    with os.fdopen(descriptor, encoding='utf-8') as stream:
        opened = os.fstat(stream.fileno())
        if (opened.st_dev, opened.st_ino) != (value.st_dev, value.st_ino):
            raise ValueError('Launch payload changed before reading')
        body = json.load(stream)
    if (not isinstance(body, dict) or set(body) != {'schema_version', 'provider', 'cwd', 'argv'}
            or type(body['schema_version']) is not int or body['schema_version'] != 1
            or body['provider'] not in ('claude', 'codex')
            or not isinstance(body['cwd'], str) or not Path(body['cwd']).is_absolute()
            or not isinstance(body['argv'], list) or not body['argv']
            or any(not isinstance(arg, str) or '\0' in arg for arg in body['argv'])
            or not Path(body['argv'][0]).is_absolute()):
        raise ValueError('Invalid native launch payload')
    path.unlink()
    return body


def run_payload(path):
    """Run on the native tty; actual lifecycle hooks remain the Provider's work."""
    body = _read_payload(path)
    child = None
    previous = {}
    termination = [None]
    inspecting = [False]

    class InspectionInterrupted(Exception):
        pass

    def forward(signum, _frame):
        termination[0] = signum
        if child is not None and child.poll() is None:
            child.send_signal(signum)
        elif inspecting[0]:
            raise InspectionInterrupted

    def inspect_failure():
        if not sys.stdin.isatty() or termination[0] is not None:
            return
        inspecting[0] = True
        try:
            if termination[0] is None:
                input('Inspect this tab, then press Enter to close it. ')
        except (EOFError, InspectionInterrupted):
            pass
        finally:
            inspecting[0] = False

    # SIGINT is delivered to the foreground group. Do not let the supervising
    # Python process interrupt its wait while the native TUI handles the key.
    for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        previous[signum] = signal.signal(signum, (lambda *_: None) if signum == signal.SIGINT else forward)
    code = 1
    try:
        os.chdir(body['cwd'])
        child = subprocess.Popen(body['argv'])
        if termination[0] is not None and child.poll() is None:
            child.send_signal(termination[0])
        code = child.wait()
        if termination[0] is None and (code or not path.with_name('started').exists()):
            print(f'\nDeskmate: {body["provider"]} exited with status {code}.', file=sys.stderr)
            inspect_failure()
    except OSError as error:
        print('Deskmate could not start the native CLI: ' + str(error), file=sys.stderr)
        inspect_failure()
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)
        shutil.rmtree(path.parent, ignore_errors=True)
    return code


if __name__ == '__main__':
    if len(sys.argv) != 3 or sys.argv[1] != '--payload':
        raise SystemExit('Internal native launch payload required')
    try:
        raise SystemExit(run_payload(Path(sys.argv[2])))
    except (OSError, ValueError) as error:
        print('Deskmate launch payload: ' + str(error), file=sys.stderr)
        raise SystemExit(2)
