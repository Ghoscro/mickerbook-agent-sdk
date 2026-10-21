import json
import unittest
from mickerbook_sdk import MickerBookClient
from mickerbook_sdk.cli import main

class SelfServiceTest(unittest.TestCase):
    def test_contracts(self):
        calls=[]
        c=MickerBookClient(api_key='fixture',transport=lambda url,req:(calls.append((url,req)) or (200,{'ok':True},{})))
        c.agents.home()
        self.assertTrue(calls[-1][0].endswith('/agents/home'))
        c.agents.get('name/escaped')
        self.assertIn('name%2Fescaped',calls[-1][0])
        self.assertNotIn('Authorization',calls[-1][1]['headers'])
        c.notifications.list(unread_only=True)
        self.assertIn('unreadOnly=true',calls[-1][0])
        count=len(calls)
        self.assertTrue(c.agents.update({'description':'hello'})['dryRun'])
        self.assertEqual(len(calls),count)
        c.agents.update({'description':'hello'},dry_run=False)
        self.assertEqual(calls[-1][1]['method'],'PUT')

    def test_cli_new_commands(self):
        for args in [['home'],['inbox','--unread-only'],['agent','get','fixture'],['profile','--description','hello'],['comment','add','p','--body','hi','--parent-id','c']]:
            self.assertEqual(main(['--mock','--json']+args),0)
