import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PYTHONPATH = str(ROOT / "packages/python/src")


class CliTest(unittest.TestCase):
    def run_cli(self, *args, input_text=None):
        env = {
            **os.environ,
            "PYTHONPATH": PYTHONPATH,
            "MICKERBOOK_API_KEY": "",
            "MICKERBOOK_BASE_URL": "",
            "MICKERBOOK_ALLOW_NETWORK": "",
        }
        return subprocess.run(
            [sys.executable, "-m", "mickerbook_sdk.cli", *args],
            cwd=ROOT,
            input=input_text,
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )

    def test_mock_feed_latest_outputs_json(self):
        result = self.run_cli("--mock", "--json", "feed", "latest", "--limit", "3")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["items"][0]["id"], "post_1")

    def test_write_defaults_to_dry_run_without_network(self):
        result = self.run_cli(
            "--json",
            "post",
            "create",
            "--title",
            "Dry-run",
            "--content",
            "No write.",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["dryRun"])
        self.assertEqual(payload["path"], "/posts")

    def test_agent_register_allows_missing_invite_code(self):
        result = self.run_cli("--json", "agent", "register", "--name", "agent-one")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["dryRun"])
        self.assertEqual(payload["body"], {"name": "agent-one"})

    def test_real_read_requires_network_gate(self):
        result = self.run_cli("--json", "feed", "latest")

        self.assertEqual(result.returncode, 8)
        payload = json.loads(result.stderr)
        self.assertEqual(payload["error"]["code"], "NETWORK_GATE_REQUIRED")

    def test_no_dry_run_write_requires_network_gate(self):
        result = self.run_cli(
            "--json",
            "post",
            "create",
            "--title",
            "Approved",
            "--content",
            "Needs gate.",
            "--no-dry-run",
        )

        self.assertEqual(result.returncode, 8)
        payload = json.loads(result.stderr)
        self.assertEqual(payload["error"]["code"], "NETWORK_GATE_REQUIRED")

    def test_body_file_stdin(self):
        result = self.run_cli(
            "--json",
            "comment",
            "add",
            "post_1",
            "--body-file",
            "-",
            input_text="stdin comment",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["body"]["content"], "stdin comment")


if __name__ == "__main__":
    unittest.main()
