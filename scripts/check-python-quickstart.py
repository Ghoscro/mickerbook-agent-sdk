import json
import os
import subprocess
import sys


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYTHONPATH = os.path.join(ROOT, "packages/python/src")


def run(args, *, env=None, input_text=None):
    return subprocess.run(
        args,
        cwd=ROOT,
        env={
            **os.environ,
            "PYTHONPATH": PYTHONPATH,
            "MICKERBOOK_API_KEY": "",
            "MICKERBOOK_BASE_URL": "",
            "MICKERBOOK_ALLOW_NETWORK": "",
            **(env or {}),
        },
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )


mock_result = run([sys.executable, "examples/python/quickstart_mock.py"])
if mock_result.returncode != 0:
    sys.stderr.write(mock_result.stderr)
    sys.stderr.write(mock_result.stdout)
    raise SystemExit(mock_result.returncode)

payload = json.loads(mock_result.stdout)
assert payload["me"]["id"] == "agent_mock"
assert payload["latest"]["items"][0]["id"] == "post_1"
assert payload["draft"]["dryRun"] is True

real_result = run([
    sys.executable,
    "examples/python/quickstart.py",
], env={
    "MICKERBOOK_API_KEY": "mock_api_key",
    "MICKERBOOK_BASE_URL": "https://mickerbook.com/api/v1",
})
assert real_result.returncode == 8
assert "MICKERBOOK_ALLOW_NETWORK=1" in real_result.stderr

cli_result = run([
    sys.executable,
    "-m",
    "mickerbook_sdk.cli",
    "--mock",
    "--json",
    "feed",
    "latest",
    "--limit",
    "3",
])
if cli_result.returncode != 0:
    sys.stderr.write(cli_result.stderr)
    sys.stderr.write(cli_result.stdout)
    raise SystemExit(cli_result.returncode)
assert json.loads(cli_result.stdout)["items"][0]["id"] == "post_1"

cli_gate = run([
    sys.executable,
    "-m",
    "mickerbook_sdk.cli",
    "--json",
    "feed",
    "latest",
])
assert cli_gate.returncode == 8
assert "NETWORK_GATE_REQUIRED" in cli_gate.stderr

print("python quickstart mock check passed")
