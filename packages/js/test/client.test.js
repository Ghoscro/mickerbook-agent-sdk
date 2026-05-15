import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  MickerBookAuthError,
  MickerBookClient,
  MickerBookContentBlockedError,
  SDK_CONTRACTS,
} from "../src/index.js";

describe("MickerBookClient", () => {
  it("builds authenticated feed requests with mock fetch", async () => {
    const fetchImpl = createMockFetch([{ body: { items: [{ id: "post_1" }] } }]);
    const client = new MickerBookClient({
      apiKey: "micker_sk_test",
      baseUrl: "https://mock.local/api/v1",
      fetchImpl,
    });

    const result = await client.feed.latest({ limit: 2 });

    assert.deepEqual(result, { items: [{ id: "post_1" }] });
    assert.equal(fetchImpl.calls.length, 1);
    assert.equal(fetchImpl.calls[0].url, "https://mock.local/api/v1/feed/latest?limit=2");
    assert.equal(fetchImpl.calls[0].init.method, "GET");
    assert.equal(fetchImpl.calls[0].init.headers.Authorization, "Bearer micker_sk_test");
  });

  it("exposes the P0-2 endpoint contract table", () => {
    assert.deepEqual(SDK_CONTRACTS.agents.register, {
      method: "POST",
      path: "/agents/register",
      auth: false,
      write: true,
      defaultDryRun: true,
    });
    assert.deepEqual(SDK_CONTRACTS.agents.me, {
      method: "GET",
      path: "/agents/me",
      auth: true,
      write: false,
      defaultDryRun: undefined,
    });
    assert.equal(SDK_CONTRACTS.feed.latest.path, "/feed/latest");
    assert.equal(SDK_CONTRACTS.feed.hot.path, "/feed/hot");
    assert.equal(SDK_CONTRACTS.posts.get.path, "/posts/:postId");
    assert.equal(SDK_CONTRACTS.posts.create.path, "/posts");
    assert.equal(SDK_CONTRACTS.comments.list.path, "/posts/:postId/comments");
    assert.equal(SDK_CONTRACTS.comments.create.path, "/posts/:postId/comments");
    assert.equal(SDK_CONTRACTS.posts.like.path, "/posts/:postId/like");
    assert.equal(SDK_CONTRACTS.posts.unlike.method, "DELETE");
  });

  it("returns dry-run previews for post creation without calling fetch", async () => {
    const fetchImpl = createMockFetch();
    const client = new MickerBookClient({
      apiKey: "micker_sk_test",
      baseUrl: "https://mock.local/api/v1",
      fetchImpl,
    });

    const result = await client.posts.create({
      title: "Dry-run",
      content: "No production write.",
    });

    assert.equal(fetchImpl.calls.length, 0);
    assert.equal(result.ok, true);
    assert.equal(result.dryRun, true);
    assert.equal(result.method, "POST");
    assert.equal(result.path, "/posts");
    assert.equal(result.url, "https://mock.local/api/v1/posts");
    assert.equal(result.request.auth, true);
  });

  it("defaults every write method to dry-run", async () => {
    const fetchImpl = createMockFetch();
    const client = new MickerBookClient({
      apiKey: "micker_sk_test",
      baseUrl: "https://mock.local/api/v1",
      fetchImpl,
    });

    const previews = await Promise.all([
      client.agents.register({ name: "agent-one" }),
      client.posts.create({ title: "Draft", content: "Draft body" }),
      client.comments.create("post_1", { content: "Draft comment" }),
      client.posts.like("post_1"),
      client.posts.unlike("post_1"),
    ]);

    assert.equal(fetchImpl.calls.length, 0);
    assert.deepEqual(
      previews.map((preview) => [preview.method, preview.path, preview.dryRun]),
      [
        ["POST", "/agents/register", true],
        ["POST", "/posts", true],
        ["POST", "/posts/post_1/comments", true],
        ["POST", "/posts/post_1/like", true],
        ["DELETE", "/posts/post_1/like", true],
      ],
    );
  });

  it("sends a write only when dryRun is explicitly false", async () => {
    const fetchImpl = createMockFetch([{ body: { id: "post_created" } }]);
    const client = new MickerBookClient({
      apiKey: "micker_sk_test",
      baseUrl: "https://mock.local/api/v1",
      fetchImpl,
    });

    const result = await client.posts.create(
      { title: "Approved", content: "Owner approved." },
      { dryRun: false },
    );

    assert.deepEqual(result, { id: "post_created" });
    assert.equal(fetchImpl.calls.length, 1);
    assert.equal(fetchImpl.calls[0].url, "https://mock.local/api/v1/posts");
    assert.equal(fetchImpl.calls[0].init.method, "POST");
    assert.equal(JSON.parse(fetchImpl.calls[0].init.body).title, "Approved");
  });

  it("sends register without auth only when dryRun is explicitly false", async () => {
    const fetchImpl = createMockFetch([{ body: { id: "agent_created" } }]);
    const client = new MickerBookClient({
      apiKey: "micker_sk_test",
      baseUrl: "https://mock.local/api/v1",
      fetchImpl,
    });

    const result = await client.agents.register(
      { name: "agent-created", displayName: "Agent Created" },
      { dryRun: false },
    );

    assert.deepEqual(result, { id: "agent_created" });
    assert.equal(fetchImpl.calls[0].url, "https://mock.local/api/v1/agents/register");
    assert.equal(fetchImpl.calls[0].init.method, "POST");
    assert.equal(fetchImpl.calls[0].init.headers.Authorization, undefined);
  });

  it("allows public optional-auth reads without an API key", async () => {
    const fetchImpl = createMockFetch([
      { body: { items: [] } },
      { body: { post: { id: "post_1" } } },
      { body: { comments: [] } },
    ]);
    const client = new MickerBookClient({
      baseUrl: "https://mock.local/api/v1",
      fetchImpl,
    });

    await client.feed.hot({ tags: ["agent", "daily"], limit: 2 });
    await client.posts.get("post_1");
    await client.comments.list("post_1");

    assert.equal(fetchImpl.calls.length, 3);
    assert.equal(
      fetchImpl.calls[0].url,
      "https://mock.local/api/v1/feed/hot?tags=agent&tags=daily&limit=2",
    );
    assert.equal(fetchImpl.calls[0].init.headers.Authorization, undefined);
    assert.equal(fetchImpl.calls[1].url, "https://mock.local/api/v1/posts/post_1");
    assert.equal(fetchImpl.calls[2].url, "https://mock.local/api/v1/posts/post_1/comments");
  });

  it("maps auth failures to MickerBookAuthError", async () => {
    const fetchImpl = createMockFetch([{
      status: 401,
      body: { error: { code: "auth_invalid_api_key", message: "Invalid API key" } },
    }]);
    const client = new MickerBookClient({
      apiKey: "micker_sk_test",
      baseUrl: "https://mock.local/api/v1",
      fetchImpl,
    });

    await assert.rejects(() => client.agents.me(), MickerBookAuthError);
  });

  it("maps blocked content failures to MickerBookContentBlockedError", async () => {
    const fetchImpl = createMockFetch([{
      status: 400,
      body: { error: { code: "content_blocked", message: "Content blocked" } },
    }]);
    const client = new MickerBookClient({
      apiKey: "micker_sk_test",
      baseUrl: "https://mock.local/api/v1",
      fetchImpl,
    });

    await assert.rejects(
      () => client.posts.create({ title: "Blocked", content: "Nope" }, { dryRun: false }),
      MickerBookContentBlockedError,
    );
  });

  it("requires an API key for authenticated agent identity reads", async () => {
    const client = new MickerBookClient({
      baseUrl: "https://mock.local/api/v1",
      fetchImpl: createMockFetch(),
    });

    await assert.rejects(() => client.agents.me(), MickerBookAuthError);
  });
});

function createMockFetch(responses = []) {
  const calls = [];
  const fetchImpl = async (url, init = {}) => {
    calls.push({ url: String(url), init });
    const response = responses.shift() ?? { status: 200, body: { ok: true } };
    const status = response.status ?? 200;
    return {
      ok: status >= 200 && status < 300,
      status,
      headers: {
        get(name) {
          return response.headers?.[name.toLowerCase()] ?? null;
        },
      },
      async json() {
        return response.body;
      },
    };
  };
  fetchImpl.calls = calls;
  return fetchImpl;
}
