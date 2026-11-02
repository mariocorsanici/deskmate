"""Shared-card behavior through the public command, using only temporary state."""
import concurrent.futures
import fcntl
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class ProjectCardsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = pathlib.Path(self.tmp.name).resolve()
        self.project = self.home / 'Demo Project'
        self.project.mkdir()
        self.env = dict(os.environ, HOME=str(self.home), DESKMATE_DATA_DIR=str(self.home / 'data'))
        self.source = self.home / 'candidate.md'
        self.body = '# Demo\n\n## Status\n- **State:** active\n\n## Checks\n- ready: `printf ready`\n'
        self.source.write_text(self.body)

    def cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'bin/deskmate'), *map(str, args)],
                              env=self.env, capture_output=True, text=True)

    def card(self, *args):
        return self.cli('card', *args)

    def locate(self, project=None):
        result = self.card('locate', project or self.project)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def write(self, revision=0, provider='codex', session='session-1'):
        return self.card('write', self.project, '--expected-revision', revision,
                         '--provider', provider, '--session-id', session, '--from', self.source)

    def legacy(self):
        key = re.sub(r'[^a-zA-Z0-9]', '-', str(self.project.resolve()))
        path = self.home / '.claude/projects' / key / 'memory/project-card.md'
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def test_identity_and_missing_card_do_not_create_state(self):
        info = self.locate()
        key = 'demo-project-' + hashlib.sha256(str(self.project).encode()).hexdigest()[:12]
        self.assertEqual(info, {'path': str(self.home / 'data/projects' / key / 'project-card.md'), 'metadata': None})
        alias = self.home / 'alias'
        alias.symlink_to(self.project)
        self.assertEqual(self.locate(alias), info)
        other = self.home / 'other/Demo Project'
        other.mkdir(parents=True)
        self.assertNotEqual(self.locate(other)['path'], info['path'])
        self.assertFalse((self.home / 'data').exists())

    def test_create_update_conflict_and_json_envelope(self):
        result = self.write()
        self.assertEqual(result.returncode, 0, result.stderr)
        info = self.locate()
        card = pathlib.Path(info['path'])
        self.assertEqual(info['metadata'], dict(schema_version=1, revision=1, provider='codex', session_id='session-1'))
        self.assertTrue(card.read_text().endswith(self.body))
        self.assertEqual(self.legacy().resolve(), card)
        old = card.read_bytes()
        self.assertEqual(self.write(1, 'claude', 'session-2').returncode, 0)
        self.assertEqual(self.locate()['metadata']['revision'], 2)
        result = self.write(1)
        self.assertEqual(result.returncode, 3)
        self.assertEqual(result.stdout, card.read_text())
        self.assertIn('2', result.stderr)
        result = self.cli('--json', 'card', 'locate', self.project)
        self.assertTrue(json.loads(result.stdout)['ok'])
        self.assertNotEqual(old, card.read_bytes())

    def test_list_is_sorted_and_validates_cards(self):
        self.assertEqual(self.card('list').stdout, '')
        self.assertEqual(self.write().returncode, 0)
        self.assertEqual(self.card('list').stdout, self.locate()['path'] + '\n')
        card = pathlib.Path(self.locate()['path'])
        card.write_text(card.read_text().replace('"schema_version":1', '"schema_version":2'))
        self.assertEqual(self.card('list').returncode, 2)

    def test_invalid_paths_and_write_arguments_create_no_storage(self):
        for path in (self.home / 'missing', self.source):
            self.assertEqual(self.card('locate', path).returncode, 2)
        for revision, provider, session in ((-1, 'codex', 'a'), (0, 'other', 'a'), (0, 'codex', ' ')):
            self.assertEqual(self.write(revision, provider, session).returncode, 2)
        self.assertFalse((self.home / 'data').exists())

    def test_rejects_invalid_metadata_before_mutation(self):
        bad = [
            '{"schema_version":2,"revision":1,"provider":null,"session_id":null}',
            '{"schema_version":true,"revision":1,"provider":null,"session_id":null}',
            '{"schema_version":1,"revision":0,"provider":null,"session_id":null}',
            '{"schema_version":1,"revision":1,"provider":"codex","session_id":null}',
            '{"schema_version":1,"revision":1,"provider":null,"session_id":null,"extra":1}',
            '{"schema_version":1,"revision":1,"provider":null,"session_id":null,"revision":2}',
            '{}', 'NaN', '[]', '{broken',
        ]
        for metadata in bad:
            with self.subTest(metadata=metadata):
                self.source.write_text('---\ndeskmate: ' + metadata + '\n---\n' + self.body)
                self.assertEqual(self.write().returncode, 2)
                self.assertFalse((self.home / 'data').exists())
        self.source.write_text('---\ndeskmate: {}\ndeskmate: {}\n---\n')
        self.assertEqual(self.write().returncode, 2)

    def test_preserves_frontmatter_and_overrides_valid_candidate_metadata(self):
        self.source.write_text('---\nname: project-card\ntype: project\ndeskmate: {"schema_version":1,"revision":99,"provider":null,"session_id":null}\n---\n' + self.body)
        self.assertEqual(self.write().returncode, 0)
        card = pathlib.Path(self.locate()['path']).read_text()
        self.assertIn('name: project-card\ntype: project\n', card)
        self.assertEqual(self.locate()['metadata']['revision'], 1)

    def test_future_stored_schema_stops_before_backup_or_link_repair(self):
        self.assertEqual(self.write().returncode, 0)
        card = pathlib.Path(self.locate()['path'])
        self.legacy().unlink()
        card.write_text(card.read_text().replace('"schema_version":1', '"schema_version":9'))
        before = card.read_bytes()
        for args in (('locate', self.project), ('migrate', self.project)):
            self.assertEqual(self.card(*args).returncode, 2)
        self.assertEqual(self.write(1).returncode, 2)
        self.assertEqual(card.read_bytes(), before)
        self.assertFalse(self.legacy().is_symlink())
        self.assertFalse((self.home / 'data/backups').exists())

    def test_migration_backup_ownership_and_repetition(self):
        legacy = self.legacy()
        raw = ('---\nname: project-card\ndescription: Keep this\ntype: project\n---\n' + self.body +
               '\nCheckpoint 2026-11-02 12:00, session `old-session`, folder `demo`.\n').encode()
        legacy.write_bytes(raw)
        self.assertEqual(self.write().returncode, 2)
        result = self.card('migrate', self.project)
        self.assertEqual(result.returncode, 0, result.stderr)
        info = self.locate()
        self.assertEqual(info['metadata']['provider'], 'claude')
        self.assertEqual(info['metadata']['session_id'], 'old-session')
        backups = list((self.home / 'data/backups').rglob('*.md'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), raw)
        self.assertEqual(backups[0].stem, hashlib.sha256(raw).hexdigest())
        card = pathlib.Path(info['path'])
        self.assertEqual(legacy.resolve(), card)
        before = card.read_bytes()
        self.assertEqual(self.card('migrate', self.project).returncode, 0)
        legacy.unlink()
        legacy.write_bytes(raw)  # interruption after installing shared card
        self.assertEqual(self.card('migrate', self.project).returncode, 0)
        self.assertEqual(card.read_bytes(), before)
        self.assertEqual(list((self.home / 'data/backups').rglob('*.md')), backups)
        legacy.unlink()
        self.locate()  # interrupted symlink installation is repaired
        self.assertTrue(legacy.is_symlink())

    def test_conflicting_legacy_and_unexpected_symlink_preserve_content(self):
        self.assertEqual(self.write().returncode, 0)
        card = pathlib.Path(self.locate()['path'])
        before = card.read_bytes()
        legacy = self.legacy()
        legacy.unlink()
        legacy.write_text('different legacy content')
        self.assertEqual(self.card('migrate', self.project).returncode, 2)
        self.assertEqual(legacy.read_text(), 'different legacy content')
        self.assertEqual(card.read_bytes(), before)
        legacy.unlink()
        outside = self.home / 'outside'
        outside.write_text('do not touch')
        legacy.symlink_to(outside)
        self.assertEqual(self.write(1).returncode, 2)
        self.assertEqual(self.card('migrate', self.project).returncode, 2)
        self.assertEqual(outside.read_text(), 'do not touch')
        self.assertEqual(card.read_bytes(), before)

    def test_missing_legacy_migration_is_noop_and_plain_body_is_lossless(self):
        result = self.card('migrate', self.project)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('no legacy', result.stdout.lower())
        legacy = self.legacy()
        raw = b'# Plain\r\n\r\nNo frontmatter.\r\n'
        legacy.write_bytes(raw)
        self.assertEqual(self.card('migrate', self.project).returncode, 0)
        info = self.locate()
        self.assertIsNone(info['metadata']['provider'])
        self.assertTrue(pathlib.Path(info['path']).read_bytes().endswith(raw))

    def test_concurrent_writers_and_atomic_replacement(self):
        self.assertEqual(self.write().returncode, 0)
        card = pathlib.Path(self.locate()['path'])
        with card.open('rb') as old:
            old_content = old.read()
            old.seek(0)
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: self.write(1), range(2)))
            self.assertEqual(sorted(r.returncode for r in results), [0, 3])
            self.assertEqual(old.read(), old_content)
        self.assertEqual(self.locate()['metadata']['revision'], 2)
        lock = card.parent / '.lock'
        with lock.open('a') as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            with concurrent.futures.ThreadPoolExecutor() as pool:
                waiting = pool.submit(self.write, 2)
                time.sleep(0.25)
                self.assertFalse(waiting.done())
                fcntl.flock(handle, fcntl.LOCK_UN)
                self.assertEqual(waiting.result(timeout=5).returncode, 0)

    def test_checks_discover_shared_cards_and_skip_standby(self):
        self.assertEqual(self.write().returncode, 0)
        result = self.cli('check')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('ready: ok  ready', result.stdout)
        self.source.write_text(self.body.replace('active', 'standby'))
        self.assertEqual(self.write(1).returncode, 0)
        self.assertIn('In stand-by: Demo', self.cli('check').stdout)
        self.assertNotIn('ready: ok', self.cli('check').stdout)
        self.assertIn('ready: ok', self.cli('check', '--all').stdout)

    def test_legacy_future_schema_rejected_before_any_storage(self):
        legacy = self.legacy()
        text = '---\ndeskmate: {"schema_version":2,"revision":1,"provider":null,"session_id":null}\n---\n# Legacy\n'
        legacy.write_text(text)
        self.assertEqual(self.card('migrate', self.project).returncode, 2)
        self.assertEqual(legacy.read_text(), text)
        self.assertFalse((self.home / 'data').exists())

    def test_latest_checkpoint_without_session_has_no_owner(self):
        self.legacy().write_text('# Legacy\nCheckpoint 2026-01-01, session `older`.\nCheckpoint 2026-02-01, folder `project`.\n')
        self.assertEqual(self.card('migrate', self.project).returncode, 0)
        metadata = self.locate()['metadata']
        self.assertIsNone(metadata['provider'])
        self.assertIsNone(metadata['session_id'])

    def test_public_command_is_executable(self):
        self.assertTrue(os.access(ROOT / 'bin/deskmate', os.X_OK))
        result = subprocess.run([str(ROOT / 'bin/deskmate'), 'card', 'list'], env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_symlink_failure_preserves_shared_card_and_locate_repairs(self):
        blocker = self.home / '.claude'
        blocker.write_text('block installation')
        self.assertEqual(self.write().returncode, 2)
        cards = list((self.home / 'data/projects').glob('*/project-card.md'))
        self.assertEqual(len(cards), 1)
        before = cards[0].read_bytes()
        blocker.unlink()
        self.assertEqual(self.locate()['metadata']['revision'], 1)
        self.assertEqual(cards[0].read_bytes(), before)
        self.assertEqual(self.legacy().resolve(), cards[0])

    def test_list_multiple_projects_is_sorted(self):
        self.assertEqual(self.write().returncode, 0)
        other = self.home / 'Alpha'
        other.mkdir()
        result = self.card('write', other, '--expected-revision', 0, '--provider', 'claude', '--session-id', 'other', '--from', self.source)
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = sorted([self.locate()['path'], self.locate(other)['path']])
        self.assertEqual(self.card('list').stdout.splitlines(), expected)
