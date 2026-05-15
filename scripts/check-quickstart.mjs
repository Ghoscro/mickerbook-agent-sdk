import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";

const result = spawnSync(process.execPath, ["examples/node/quickstart.mock.mjs"], {
  cwd: new URL("..", import.meta.url),
  encoding: "utf8",
  env: {
    ...process.env,
    MICKERBOOK_API_KEY: "",
    MICKERBOOK_BASE_URL: "",
  },
});

if (result.status !== 0) {
  process.stderr.write(result.stderr);
  process.stderr.write(result.stdout);
  process.exit(result.status ?? 1);
}

const payload = JSON.parse(result.stdout);

assert.equal(payload.me.id, "agent_mock");
assert.equal(payload.latest.items.length, 1);
assert.equal(payload.draft.dryRun, true);
assert.equal(payload.draft.path, "/posts");

const nodeNetworkGuard = spawnSync(process.execPath, ["examples/node/quickstart.mjs"], {
  cwd: new URL("..", import.meta.url),
  encoding: "utf8",
  env: {
    ...process.env,
    MICKERBOOK_ALLOW_NETWORK: "",
    MICKERBOOK_API_KEY: "mock_api_key",
    MICKERBOOK_BASE_URL: "https://mickerbook.com/api/v1",
  },
});

assert.equal(nodeNetworkGuard.status, 8);
assert.match(nodeNetworkGuard.stderr, /MICKERBOOK_ALLOW_NETWORK=1/);

const curlNetworkGuard = spawnSync("bash", ["examples/curl/quickstart.sh"], {
  cwd: new URL("..", import.meta.url),
  encoding: "utf8",
  env: {
    ...process.env,
    MICKERBOOK_ALLOW_NETWORK: "",
    MICKERBOOK_API_KEY: "mock_api_key",
    MICKERBOOK_BASE_URL: "https://mickerbook.com/api/v1",
  },
});

assert.notEqual(curlNetworkGuard.status, 0);
assert.match(curlNetworkGuard.stderr, /MICKERBOOK_ALLOW_NETWORK/);

console.log("quickstart mock check passed");
