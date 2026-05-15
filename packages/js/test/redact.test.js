import assert from "node:assert/strict";
import { describe, it } from "node:test";

import { redactSecrets } from "../src/index.js";

describe("redactSecrets", () => {
  it("redacts MickerBook API keys in strings", () => {
    const fakeKey = ["micker", "sk", "1234567890abcdef"].join("_");
    assert.equal(
      redactSecrets(`key=${fakeKey}`),
      "key=[REDACTED]",
    );
  });

  it("redacts bearer tokens", () => {
    assert.equal(
      redactSecrets("Authorization: Bearer abc.def.ghi"),
      "Authorization: Bearer [REDACTED]",
    );
  });

  it("redacts nested values", () => {
    assert.deepEqual(
      redactSecrets({
        headers: { Authorization: "Bearer secret-token" },
        body: ["apiKey=secret-key"],
      }),
      {
        headers: { Authorization: "Bearer [REDACTED]" },
        body: ["apiKey=[REDACTED]"],
      },
    );
  });
});
