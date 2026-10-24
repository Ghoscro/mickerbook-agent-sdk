import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from mickerbook_sdk import update


class UpdatePathsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        # Canonical fixture paths isolate protection tests from system aliases.
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / 'managed'
        self.root.mkdir()
        self.outside = self.base / 'outside'
        self.outside.mkdir()
        self.sentinel = self.outside / 'keep'
        self.sentinel.write_text('unchanged')
        self.files = {name: name.encode() for name in update.FILES}
        self.manifest = {'schemaVersion': 1, 'skillVersion': '3.1.0', 'skillFiles': {
            name: {'url': 'https://mickerbook.com/sdk/' + name, 'sha256': update.digest(data)}
            for name, data in self.files.items()}}
        self.download = patch.object(update, 'download', side_effect=self.mock_download).start()
        self.addCleanup(patch.stopall)

    def mock_download(self, url, *args):
        return json.dumps(self.manifest).encode() if url == update.MANIFEST else self.files[url.rsplit('/', 1)[1]]

    def assert_outside_unchanged(self):
        self.assertEqual(list(self.outside.iterdir()), [self.sentinel])
        self.assertEqual(self.sentinel.read_text(), 'unchanged')

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS system aliases')
    def test_system_alias_install_and_canonical_state_are_identical(self):
        # Exercise both system temporary-directory spellings, including a root
        # that does not yet exist; no TMPDIR override or resolve at the call site.
        for alias in ['/var/tmp', '/tmp']:
            with self.subTest(alias=alias), tempfile.TemporaryDirectory(dir=alias) as directory:
                root = Path(directory) / 'new-managed'
                self.assertTrue(update.sync(root, apply=True)['updated'])
                for name, data in self.files.items():
                    self.assertEqual((root.resolve() / name).read_bytes(), data)
                self.assertFalse(update.sync(root.resolve())['updateAvailable'])

    def test_managed_root_and_custom_ancestor_links_are_rejected(self):
        for target in [self.outside, self.base / 'missing']:
            link = self.base / 'link'
            link.symlink_to(target, target_is_directory=True)
            try:
                for root in [link, link / 'child']:
                    with self.subTest(root=root), self.assertRaisesRegex(ValueError, 'symlink'):
                        update.sync(root, apply=True)
            finally:
                link.unlink()
        self.download.assert_not_called()
        self.assert_outside_unchanged()

    def test_managed_files_state_and_backup_links_are_rejected(self):
        for name in [update.STATE, '.previous', *sorted(update.FILES)]:
            for target in [self.sentinel, self.base / 'missing']:
                link = self.root / name
                link.symlink_to(target)
                try:
                    with self.subTest(name=name, target=target), self.assertRaisesRegex(ValueError, 'symlink'):
                        update.sync(self.root, apply=True)
                finally:
                    link.unlink()
                self.assert_outside_unchanged()
                self.assertEqual(list(self.root.iterdir()), [])

    def test_parent_traversal_cannot_hide_a_symlink(self):
        link = self.root / 'link'
        link.symlink_to(self.outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            update.sync(link / '..' / 'new-managed', apply=True)
        self.download.assert_not_called()
        self.assert_outside_unchanged()

    def test_alias_exceptions_require_darwin_root_ownership_and_exact_target(self):
        # Model the root-level alias metadata without modifying the host OS.
        path = Path('/var/test-managed')
        for platform, uid, target in [('linux', 0, 'private/var'), ('darwin', 501, 'private/var'), ('darwin', 0, 'elsewhere'), ('darwin', 0, 'private/var/../var')]:
            with self.subTest(platform=platform, uid=uid, target=target):
                with patch.object(update.sys, 'platform', platform), \
                     patch.object(Path, 'is_symlink', lambda p: p == Path('/var')), \
                     patch.object(Path, 'lstat', return_value=SimpleNamespace(st_uid=uid)), \
                     patch.object(os, 'readlink', return_value=target):
                    with self.assertRaisesRegex(ValueError, 'symlink'):
                        update._managed_root(path)
        self.download.assert_not_called()

    def test_canonical_target_is_checked_again_and_alias_cannot_be_root(self):
        for extra in [Path('/private'), Path('/private/var/test-managed')]:
            with self.subTest(extra=extra), patch.object(update.sys, 'platform', 'darwin'), \
                 patch.object(Path, 'is_symlink', lambda p: p in (Path('/var'), extra)), \
                 patch.object(Path, 'lstat', return_value=SimpleNamespace(st_uid=0)), \
                 patch.object(os, 'readlink', return_value='private/var'):
                with self.assertRaisesRegex(ValueError, 'symlink'):
                    update._managed_root('/var/test-managed')
        with patch.object(update.sys, 'platform', 'darwin'), \
             patch.object(Path, 'is_symlink', lambda p: p == Path('/var')):
            with self.assertRaisesRegex(ValueError, 'symlink'):
                update._managed_root('/var')

    @unittest.skipUnless(sys.platform == 'darwin', 'macOS system aliases')
    def test_custom_link_below_system_alias_is_still_rejected(self):
        with tempfile.TemporaryDirectory(dir='/tmp') as directory:
            link = Path(directory) / 'link'
            link.symlink_to(self.outside, target_is_directory=True)
            for root in [link, link / 'nested']:
                with self.subTest(root=root), self.assertRaisesRegex(ValueError, 'symlink'):
                    update.sync(root, apply=True)
        self.download.assert_not_called()
        self.assert_outside_unchanged()

    def test_only_known_root_aliases_are_translated_without_resolving(self):
        for alias in ['/var', '/tmp', '/etc']:
            for target in ['private' + alias, '/private' + alias]:
                with self.subTest(alias=alias, target=target), \
                     patch.object(update.sys, 'platform', 'darwin'), \
                     patch.object(Path, 'is_symlink', lambda p: p == Path(alias)), \
                     patch.object(Path, 'lstat', return_value=SimpleNamespace(st_uid=0)), \
                     patch.object(os, 'readlink', return_value=target), \
                     patch.object(Path, 'resolve', side_effect=AssertionError('must not resolve')):
                    self.assertEqual(update._managed_root(alias + '/managed'), Path('/private' + alias + '/managed'))
