import test from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { fileURLToPath } from "node:url";
import { createHandler } from "../../../mickerbook-mcp-server.js";

const rpc = (method, params = {}, id = 1) => ({ jsonrpc: "2.0", id, method, params });
test("MCP initialization, discovery, disabled networking and invalid writes", async () => {
  let calls = 0;
  const handle = createHandler({ fetchImpl: () => { calls++; throw new Error("unexpected"); } });
  assert.equal((await handle(rpc("tools/list"))).error.code, -32000);
  assert.equal((await handle(rpc("initialize", { protocolVersion: "2025-06-18" }))).result.protocolVersion, "2025-06-18");
  assert.equal((await handle(rpc("tools/list"))).result.tools.length, 3);
  assert.equal((await handle(rpc("tools/call", { name: "recent_posts" }))).result.isError, true);
  assert.equal((await handle(rpc("tools/call", { name: "create_post" }))).error.code, -32602);
  assert.equal(await handle({ jsonrpc: "2.0", method: "notifications/initialized" }), undefined);
  assert.equal(calls, 0);
});
test("MCP uses anonymous GETs and validates paths and limits", async () => {
  const requests = [];
  const handle = createHandler({ allowNetwork: true, fetchImpl: async (url, options) => {
    requests.push({ url, options });
    return new Response(JSON.stringify({ posts: [{ id: "fake_1", title: "Mock post" }] }), { status: 200 });
  } });
  await handle(rpc("initialize"));
  for (const tool of ["recent_posts", "get_post", "get_comments"]) {
    const result = await handle(rpc("tools/call", { name: tool, arguments: tool === "recent_posts" ? { limit: 2 } : { post_id: "fake_1" } }));
    assert.equal(result.result.isError, undefined);
    assert.equal(JSON.parse(result.result.content[0].text).untrusted_content, true);
  }
  for (const args of [{ limit: 0 }, { limit: 21 }, { limit: "3" }, { other: 1 }]) assert.equal((await handle(rpc("tools/call", { name: "recent_posts", arguments: args }))).error.code, -32602);
  assert.equal((await handle(rpc("tools/call", { name: "get_post", arguments: { post_id: "../../secret" } }))).error.code, -32602);
  assert.equal(requests.length, 3);
  assert.ok(requests.every(({ url, options }) => url.startsWith("https://mickerbook.com/api/v1/") && options.method === "GET" && options.redirect === "error" && !options.headers.Authorization));
});
test("stdio entrypoint emits only newline JSON and survives malformed input", async () => {
  const child = spawn(process.execPath, [fileURLToPath(new URL("../../../mickerbook-mcp-server.js", import.meta.url))], { env: { ...process.env, MICKERBOOK_ALLOW_NETWORK: "0" } });
  let stdout = "", stderr = "";
  child.stdout.on("data", (chunk) => { stdout += chunk; });
  child.stderr.on("data", (chunk) => { stderr += chunk; });
  const closed = new Promise((resolve) => child.on("close", resolve));
  child.stdin.end("broken\n" + JSON.stringify(rpc("initialize")) + "\n" + JSON.stringify(rpc("tools/list", {}, 2)) + "\n");
  assert.equal(await closed, 0);
  assert.equal(stderr, "");
  const lines = stdout.trim().split("\n").map(JSON.parse);
  assert.equal(lines.length, 3);
  assert.equal(lines[0].error.code, -32700);
  assert.equal(lines[2].result.tools.length, 3);
});
test("HTTP 200 HTML, null and oversized responses return tool errors", async () => {
  for (const body of ["<html>upstream error</html>", "null", "x".repeat(2_000_001)]) {
    const handle = createHandler({ allowNetwork: true, fetchImpl: async () => new Response(body, { status: 200 }) });
    await handle(rpc("initialize"));
    const response = await handle(rpc("tools/call", { name: "recent_posts" }));
    assert.equal(response.result.isError, true);
  }
});
