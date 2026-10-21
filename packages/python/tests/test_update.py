import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from mickerbook_sdk import update


class UpdateTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.files = {name: (name + ' release one').encode() for name in update.FILES}
        self.manifest = {'schemaVersion':1, 'skillVersion':'3.1.0', 'skillFiles':{name:{'url':'https://mickerbook.com/sdk/'+name, 'sha256':update.digest(data)} for name,data in self.files.items()}}

    def download(self, url, *args):
        return json.dumps(self.manifest).encode() if url == update.MANIFEST else self.files[url.rsplit('/',1)[1]]

    def test_check_install_enable_auto_and_local_edit_protection(self):
        with patch.object(update, 'download', self.download):
            self.assertTrue(update.sync(self.root)['updateAvailable'])
            self.assertFalse((self.root/'SKILL.md').exists())
            self.assertTrue(update.sync(self.root, enable_auto=True)['updated'])
            self.assertTrue(update.sync(self.root, auto=True)['cached'])
            (self.root/'SKILL.md').write_text('local instructions')
            self.manifest['skillVersion']='3.2.0'
            with self.assertRaisesRegex(ValueError,'Local changes'):
                update.sync(self.root, apply=True)
            self.assertEqual((self.root/'SKILL.md').read_text(),'local instructions')
            self.assertFalse(update.sync(self.root, disable_auto=True)['autoUpdate'])

    def test_checksum_and_downgrade_refused_without_partial_install(self):
        with patch.object(update,'download',self.download):
            self.manifest['skillFiles']['update.py']['sha256']='0'*64
            with self.assertRaisesRegex(ValueError,'Checksum'):
                update.sync(self.root,apply=True)
            self.assertFalse((self.root/'SKILL.md').exists())
            self.manifest['skillFiles']['update.py']['sha256']=update.digest(self.files['update.py'])
            update.sync(self.root,apply=True)
            self.manifest['skillVersion']='3.0.0'
            with self.assertRaisesRegex(ValueError,'Downgrade'):
                update.sync(self.root,apply=True)

    def test_network_and_path_boundaries(self):
        for url in ['http://mickerbook.com/sdk/a','https://evil.test/a','https://mickerbook.com@evil.test/a']:
            with self.assertRaises(ValueError): update.download(url)
        self.manifest['skillFiles']['../secret']={}
        with patch.object(update,'download',self.download):
            with self.assertRaises(ValueError): update.sync(self.root,apply=True)

    def test_future_release_is_applied_when_auto_enabled(self):
        with patch.object(update,'download',self.download):
            update.sync(self.root,enable_auto=True)
            previous=(self.root/'SKILL.md').read_bytes()
            self.manifest['skillVersion']='3.2.0'
            self.files['SKILL.md']=b'new release instructions'
            self.manifest['skillFiles']['SKILL.md']['sha256']=update.digest(self.files['SKILL.md'])
            state_path=self.root/update.STATE
            state=json.loads(state_path.read_text())
            state['checkedAt']=0
            state_path.write_text(json.dumps(state))
            result=update.sync(self.root,auto=True)
            self.assertTrue(result['updated'])
            self.assertEqual(result['installedVersion'],'3.2.0')
            self.assertEqual((self.root/'.previous/SKILL.md').read_bytes(),previous)
            self.assertEqual((self.root/'SKILL.md').read_bytes(),self.files['SKILL.md'])
