import assert from "node:assert/strict";
import { describe, it } from "node:test";

import {
  MickerBookAuthError,
  MickerBookClient,
  MickerBookContentBlockedError,
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

  it("requires an API key for authenticated reads", async () => {
    const client = new MickerBookClient({
      baseUrl: "https://mock.local/api/v1",
      fetchImpl: createMockFetch(),
    });

    await assert.rejects(() => client.feed.hot({ limit: 1 }), MickerBookAuthError);
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

