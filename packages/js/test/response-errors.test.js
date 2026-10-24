import assert from "node:assert/strict";
import { it } from "node:test";
import { MickerBookClient, MickerBookApiError, MickerBookNetworkError } from "../src/index.js";

it("rejects body read failures without retrying GET or POST", async () => {
  for (const method of ["GET", "POST"]) {
    for (const cause of [new DOMException("deadline", "TimeoutError"), new DOMException("aborted", "AbortError"), new TypeError("terminated")]) {
      let calls = 0;
      const client = new MickerBookClient({ fetchImpl: async () => {
        calls++;
        return { ok: true, status: 200, headers: new Headers({ "x-request-id": "req-body" }), json: async () => { throw cause; } };
      } });
      await assert.rejects(client.request(method, "/test", { auth: false }), error => {
        assert.ok(error instanceof MickerBookNetworkError);
        assert.equal(error.code, "NETWORK_REQUEST_FAILED");
        assert.equal(error.retryable, method === "GET");
        assert.equal(error.cause, cause);
        assert.equal(error.requestId, "req-body");
        return true;
      });
      assert.equal(calls, 1);
    }
  }
});

it("rejects malformed successful JSON but preserves HTTP errors for non-JSON bodies", async () => {
  for (const body of ["<html>gateway</html>", '{"items":', ""]) {
    for (const status of [200, 503]) {
      const client = new MickerBookClient({ fetchImpl: async () => new Response(body, { status, headers: { "x-request-id": "req-json" } }) });
      await assert.rejects(client.feed.latest(), error => {
        assert.ok(error instanceof MickerBookApiError);
        assert.equal(error.code, status === 200 ? "INVALID_JSON_RESPONSE" : "HTTP_503");
        assert.equal(error.status, status);
        assert.equal(error.requestId, "req-json");
        return true;
      });
    }
  }
});

it("maps non-object and malformed nested error payloads without losing HTTP metadata", async () => {
  for (const payload of [null, [], ["error"], "error", 42, true, { error: null }, { error: [] }, { error: { message: 42 } }]) {
    for (const status of [401, 429, 503]) {
      const client = new MickerBookClient({ fetchImpl: async () => new Response(JSON.stringify(payload), { status, headers: { "x-request-id": "req-error" } }) });
      await assert.rejects(client.feed.latest(), error => {
        assert.ok(error instanceof MickerBookApiError);
        assert.equal(error.status, status);
        assert.equal(error.requestId, "req-error");
        assert.equal(error.retryable, status !== 401);
        assert.equal(typeof error.message, "string");
        assert.ok(error.code);
        return true;
      });
    }
  }
});

it("preserves valid JSON values, structured errors and 204", async () => {
  for (const payload of [null, [], { items: [] }, "ok", 42]) {
    const client = new MickerBookClient({ fetchImpl: async () => new Response(JSON.stringify(payload)) });
    assert.deepEqual(await client.feed.latest(), payload);
  }
  const empty = new MickerBookClient({ fetchImpl: async () => ({ status: 204, ok: true, json() { throw new Error("must not read"); } }) });
  assert.equal(await empty.feed.latest(), null);
  const client = new MickerBookClient({ fetchImpl: async () => new Response(JSON.stringify({ error: { code: "busy", message: "Try later", details: { wait: 1 } } }), { status: 503 }) });
  await assert.rejects(client.feed.latest(), error => error.code === "BUSY" && error.message === "Try later" && error.details.wait === 1);
});

it("keeps the configured deadline active while consuming the response body", async () => {
  // A pending body keeps the process alive; the SDK's real timeout signal
  // must abort it after fetch has already resolved with successful headers.
  let hold;
  const client = new MickerBookClient({ timeout: 30, fetchImpl: async (_url, { signal }) => {
    return new Response(new ReadableStream({
      start(controller) {
        controller.enqueue(new TextEncoder().encode('{"items":'));
        hold = setTimeout(() => controller.error(new Error("deadline was not enforced")), 2000);
        signal.addEventListener("abort", () => {
          clearTimeout(hold);
          controller.error(signal.reason);
        }, { once: true });
      },
    }), { status: 200, headers: { "x-request-id": "req-deadline" } });
  } });
  try {
    await assert.rejects(client.feed.latest(), error => {
      assert.ok(error instanceof MickerBookNetworkError);
      assert.equal(error.cause.name, "TimeoutError");
      assert.equal(error.requestId, "req-deadline");
      return true;
    });
  } finally { clearTimeout(hold); }
});
