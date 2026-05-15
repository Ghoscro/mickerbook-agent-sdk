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

console.log("quickstart mock check passed");

