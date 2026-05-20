#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "..");
const pythonSrc = path.join(root, "packages", "python", "src");
const args = process.argv.slice(2);

if (args.length === 0) {
  console.error("Usage: node scripts/run-python.mjs <python args...>");
  process.exit(2);
}

const env = {
  ...process.env,
  PYTHONPATH: [pythonSrc, process.env.PYTHONPATH].filter(Boolean).join(path.delimiter),
};

const candidates = [];
if (process.env.PYTHON) candidates.push(process.env.PYTHON);
candidates.push(process.platform === "win32" ? "python" : "python3", "python3", "python");

let lastError = null;
for (const candidate of [...new Set(candidates)]) {
  const result = spawnSync(candidate, args, {
    cwd: root,
    env,
    stdio: "inherit",
    shell: false,
  });

  if (result.error) {
    if (result.error.code === "ENOENT") {
      lastError = result.error;
      continue;
    }
    console.error(result.error.message);
    process.exit(1);
  }

  process.exit(result.status ?? 0);
}

console.error("Python executable not found. Set PYTHON to a Python 3 interpreter.");
if (lastError) console.error(lastError.message);
process.exit(127);
