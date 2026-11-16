"""logins.py: morning login check, read-only, exit codes only (Daily loop L08)."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SECRET = 'ya29.SECRET-TOKEN'

# Fake CLIs: each appends its argv to calls.log, then behaves as FAKE_<NAME> says.
FAKE = r'''#!/bin/sh
echo "$(basename "$0") $*" >> "$CALLS"
name=$(basename "$0" | tr 'a-z-' 'A-Z_')
eval "mode=\${FAKE_$name:-ok}"
case "$(basename "$0") $1 $2" in
  "ssh-keygen -lf "*) echo "256 SHA256:keyprint me@mac (ED25519)"; exit 0 ;;
esac
if [ "$mode" = ok ]; then
  case "$(basename "$0")" in
    ssh-add) echo "256 SHA256:keyprint me@mac (ED25519)" ;;
    gcloud) echo "%s" ;;
    op) echo "URL: my.1password.com" ;;
  esac
  exit 0
fi
[ "$mode" = slow ] && sleep 30
echo "not signed in" >&2
exit 1
''' % SECRET


def card(title, logins, state='active'):
    return (f'# {title}\n\n## Status\n- **State:** {state}\n\n## Checks\n\n'
            '## Logins\n' + ''.join(f'- {line}\n' for line in logins))


class Logins(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name)
        self.bin = self.home / 'bin'
        self.bin.mkdir()
        for name in ('ssh-add', 'ssh-keygen', 'gcloud', 'op'):
            path = self.bin / name
            path.write_text(FAKE)
            path.chmod(0o755)
        (self.home / '.ssh').mkdir()
        (self.home / '.ssh' / 'work_key.pub').write_text('ssh-ed25519 AAAA me@mac\n')
        self.calls_file = self.home / 'calls.log'
        self.env = {'HOME': str(self.home), 'PATH': f'{self.bin}:/usr/bin:/bin', 'CALLS': str(self.calls_file),
                    'DESKMATE_DATA_DIR': str(self.home / 'data')}

    def add(self, key, title, logins, state='active'):
        path = self.home / 'data' / 'projects' / key / 'project-card.md'
        path.parent.mkdir(parents=True)
        path.write_text(card(title, logins, state), encoding='utf-8')
        return path

    def run_logins(self, *args, rc=0, **fake):
        env = {**self.env, **{f'FAKE_{k.upper()}': v for k, v in fake.items()}}
        result = subprocess.run([sys.executable, '-I', '-B', str(ROOT / 'tools' / 'logins.py'), *args],
                                capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(result.returncode, rc, result.stderr)
        self.assertNotIn(SECRET, result.stdout + result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        return json.loads(result.stdout) if rc == 0 else result

    def calls(self):
        return self.calls_file.read_text().splitlines() if self.calls_file.exists() else []

    def assert_no_fix_ran(self):
        for call in self.calls():
            self.assertNotIn(' login', call)
            self.assertFalse(call.startswith('ssh-add ') and call != 'ssh-add -l', call)
            self.assertFalse(call.startswith('op ') and call != 'op whoami', call)

    def test_all_valid_logins_report_ok(self):
        self.add('-Users-me-Dev-fleet', 'Fleet', ['ssh-key ~/.ssh/work_key', 'gcloud', 'gcloud-adc', '1password'])
        out = self.run_logins('fleet')
        self.assertTrue(out['all_ok'])
        self.assertEqual([l['status'] for l in out['logins']], ['ok'] * 4)
        self.assert_no_fix_ran()

    def test_failing_logins_get_their_fix_command_and_nothing_runs_it(self):
        self.add('-Users-me-Dev-fleet', 'Fleet', ['ssh-key ~/.ssh/work_key', 'gcloud', 'gcloud-adc'])
        out = self.run_logins('fleet', ssh_add='fail', gcloud='fail')
        self.assertFalse(out['all_ok'])
        fixes = {l['login']: l['fix'] for l in out['logins'] if l['status'] == 'missing'}
        self.assertEqual(fixes, {
            'ssh-key ~/.ssh/work_key': f'ssh-add {self.home}/.ssh/work_key',
            'gcloud': 'gcloud auth login',
            'gcloud-adc': 'gcloud auth application-default login',
        })
        self.assert_no_fix_ran()

    def test_ssh_key_must_be_the_one_loaded_in_the_agent(self):
        self.add('-Users-me-Dev-fleet', 'Fleet', ['ssh-key ~/.ssh/work_key'])
        (self.bin / 'ssh-add').write_text('#!/bin/sh\necho "ssh-add $*" >> "$CALLS"\necho "256 SHA256:other x (ED25519)"\n')
        out = self.run_logins('fleet')
        self.assertEqual(out['logins'][0]['status'], 'missing')

    def test_1password_not_signed_in_is_a_warning_with_a_touch_id_command(self):
        self.add('-Users-me-Dev-fleet', 'Fleet', ['1password'])
        out = self.run_logins('fleet', op='fail')
        login = out['logins'][0]
        self.assertEqual(login['status'], 'warning')
        self.assertEqual(login['fix'], 'op vault list >/dev/null')
        self.assertTrue(out['all_ok'])
        self.assert_no_fix_ran()

    def test_logins_are_deduplicated_across_cards_with_their_projects(self):
        self.add('-Users-me-Dev-fleet', 'Fleet', ['gcloud'])
        self.add('-Users-me-Dev-vlm', 'VLM', ['gcloud', 'gcloud-adc'])
        out = self.run_logins('fleet', 'vlm')
        self.assertEqual([(l['login'], l['projects']) for l in out['logins']],
                         [('gcloud', ['Fleet', 'VLM']), ('gcloud-adc', ['VLM'])])
        self.assertEqual(sum(c.startswith('gcloud auth print-access-token') for c in self.calls()), 1)

    def test_without_arguments_every_active_card_is_checked(self):
        self.add('-Users-me-Dev-fleet', 'Fleet', ['gcloud'])
        self.add('-Users-me-Dev-old', 'Old', ['gcloud-adc'], state='closed')
        self.add('-Users-me-Dev-wait', 'Waiting', ['1password'], state='standby')
        out = self.run_logins()
        self.assertEqual([l['login'] for l in out['logins']], ['gcloud'])

    def test_cards_without_logins_give_an_empty_ok_result(self):
        self.add('-Users-me-Dev-fleet', 'Fleet', [])
        out = self.run_logins('fleet')
        self.assertEqual(out['logins'], [])
        self.assertTrue(out['all_ok'])

    def test_missing_cli_is_unavailable_not_ok(self):
        self.add('-Users-me-Dev-fleet', 'Fleet', ['gcloud'])
        (self.bin / 'gcloud').unlink()
        out = self.run_logins('fleet')
        self.assertEqual(out['logins'][0]['status'], 'unavailable')
        self.assertFalse(out['all_ok'])

    def test_unknown_login_type_is_reported(self):
        self.add('-Users-me-Dev-fleet', 'Fleet', ['vpn-corp'])
        out = self.run_logins('fleet')
        self.assertEqual(out['logins'][0]['status'], 'unknown')
        self.assertFalse(out['all_ok'])

    def test_slow_check_is_unavailable_without_a_fix(self):
        self.add('-Users-me-Dev-fleet', 'Fleet', ['gcloud'])
        out = self.run_logins('fleet', gcloud='slow')
        login = out['logins'][0]
        self.assertEqual((login['status'], login['fix']), ('unavailable', ''))
        self.assertIn('timeout', login['detail'])

    def test_no_ssh_agent_is_unavailable_without_a_fix(self):
        self.add('-Users-me-Dev-fleet', 'Fleet', ['ssh-key ~/.ssh/work_key'])
        (self.bin / 'ssh-add').write_text('#!/bin/sh\necho "ssh-add $*" >> "$CALLS"\nexit 2\n')
        login = self.run_logins('fleet')['logins'][0]
        self.assertEqual((login['status'], login['fix']), ('unavailable', ''))
        self.assertIn('no SSH agent', login['detail'])

    def test_key_path_with_spaces_is_quoted_in_the_fix(self):
        (self.home / 'my keys').mkdir()
        (self.home / 'my keys' / 'k.pub').write_text('ssh-ed25519 AAAA me@mac\n')
        self.add('-Users-me-Dev-fleet', 'Fleet', ['ssh-key ~/my keys/k'])
        login = self.run_logins('fleet', ssh_add='fail')['logins'][0]
        self.assertEqual(login['fix'], f"ssh-add '{self.home}/my keys/k'")

    def test_unknown_project_name_fails_without_traceback(self):
        self.add('-Users-me-Dev-fleet', 'Fleet', ['gcloud'])
        result = self.run_logins('nothing', rc=1)
        self.assertIn('Fleet', result.stderr)


if __name__ == '__main__':
    unittest.main()
