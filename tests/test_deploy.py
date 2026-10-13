"""Проверки границ SSH-деплоя и возврата предыдущей версии."""
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import types
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    'deploy_site', Path(__file__).resolve().parents[1] / 'deploy/server/deploy-site.py')
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)
RELEASE = 'a' * 40 + '-1-1'


def archive(entries):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode='w:gz') as bundle:
        for name, content in entries:
            member = tarfile.TarInfo(name)
            if content is None:
                member.type = tarfile.SYMTYPE
                member.linkname = '/etc/passwd'
                bundle.addfile(member)
            else:
                member.size = len(content)
                bundle.addfile(member, io.BytesIO(content))
    return output.getvalue()


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.old = self.base / 'releases/previous'
        self.old.mkdir(parents=True)
        (self.old / 'index.html').write_bytes(b'previous page')
        (self.base / 'current').symlink_to('releases/previous')
        base_patch = patch.object(deploy, 'BASE', self.base)
        base_patch.start()
        self.addCleanup(base_patch.stop)

    def publish(self, entries, check_error=None):
        stdin = types.SimpleNamespace(buffer=io.BytesIO(archive(entries)))
        with patch.object(deploy.sys, 'stdin', stdin), patch.object(
                deploy, 'check_published_index', side_effect=check_error) as check:
            deploy.publish(RELEASE)
            return check

    def test_success_switches_complete_release_and_preserves_previous(self):
        check = self.publish([('index.html', b'new page'), ('assets/app.js', b'new script')])
        release = self.base / 'releases' / RELEASE
        self.assertEqual((self.base / 'current').resolve(), release)
        self.assertEqual((release / 'assets/app.js').read_bytes(), b'new script')
        self.assertEqual((release / 'index.html').stat().st_mode & 0o777, 0o644)
        self.assertEqual(self.old.joinpath('index.html').read_bytes(), b'previous page')
        check.assert_called_once_with(release)

    def test_failed_https_restores_previous_release(self):
        with self.assertRaisesRegex(RuntimeError, 'HTTPS failed'):
            self.publish([('index.html', b'new page')], RuntimeError('HTTPS failed'))
        self.assertEqual(os.readlink(self.base / 'current'), 'releases/previous')
        self.assertFalse(list(self.base.glob('.current-*')))

    def test_archive_rejects_traversal_hidden_files_links_and_duplicates(self):
        for entries in [
            [('../escape', b'bad')], [('/absolute', b'bad')],
            [('.env', b'bad')], [('assets/.hidden', b'bad')],
            [('link', None)], [('index.html', b'one'), ('index.html', b'two')],
            [('assets/app.js', b'no index')], [('index.html', b'')],
        ]:
            with self.subTest(entries=entries), self.assertRaises((ValueError, FileExistsError)):
                self.publish(entries)
            self.assertEqual(os.readlink(self.base / 'current'), 'releases/previous')
            self.assertFalse(list(self.base.joinpath('releases').glob('.upload-*')))
        self.assertFalse((self.base / 'escape').exists())

    def test_corrupt_archive_does_not_switch(self):
        stdin = types.SimpleNamespace(buffer=io.BytesIO(b'not gzip'))
        with patch.object(deploy.sys, 'stdin', stdin), self.assertRaises(tarfile.ReadError):
            deploy.publish(RELEASE)
        self.assertEqual(os.readlink(self.base / 'current'), 'releases/previous')

    def test_archive_and_content_limits(self):
        with patch.object(deploy, 'MAX_ARCHIVE_BYTES', 16), self.assertRaises(ValueError):
            self.publish([('index.html', b'page')])
        with patch.object(deploy, 'MAX_CONTENT_BYTES', 3), self.assertRaises(ValueError):
            self.publish([('index.html', b'page')])
        with patch.object(deploy, 'MAX_FILES', 1), self.assertRaises(ValueError):
            self.publish([('index.html', b'page'), ('assets/app.js', b'js')])
        self.assertEqual(os.readlink(self.base / 'current'), 'releases/previous')

    def test_existing_release_is_never_overwritten(self):
        release = self.base / 'releases' / RELEASE
        release.mkdir()
        (release / 'index.html').write_bytes(b'keep')
        with self.assertRaises(ValueError):
            self.publish([('index.html', b'replace')])
        self.assertEqual((release / 'index.html').read_bytes(), b'keep')

    def test_arbitrary_ssh_commands_are_denied(self):
        for command in ['', 'bash', 'deploy ../escape', f'deploy {RELEASE}; id',
                        f'deploy {RELEASE} extra', 'deploy a-1-1']:
            with self.subTest(command=command), patch.dict(
                    os.environ, {'SSH_ORIGINAL_COMMAND': command}), self.assertRaises(ValueError):
                deploy.main()

    def test_https_must_return_exact_index_from_new_release(self):
        result = subprocess.CompletedProcess([], 0, stdout=b'previous page')
        with patch.object(deploy.subprocess, 'run', return_value=result) as run:
            deploy.check_published_index(self.old)
            args = run.call_args.args[0]
            self.assertIn('mkulikov.com:443:127.0.0.1', args)
            self.assertIn('https://mkulikov.com/', args)
            self.assertNotIn('--insecure', args)
        with patch.object(deploy.subprocess, 'run', return_value=
                          subprocess.CompletedProcess([], 0, stdout=b'wrong page')):
            with self.assertRaisesRegex(RuntimeError, 'different version'):
                deploy.check_published_index(self.old)


if __name__ == '__main__':
    unittest.main()
