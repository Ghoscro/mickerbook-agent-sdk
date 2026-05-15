export function redactSecrets(value) {
  if (typeof value === "string") {
    return value
      .replace(/micker_sk_[A-Za-z0-9_-]+/g, "[REDACTED]")
      .replace(/(Bearer\s+)[A-Za-z0-9._~+/-]+=*/gi, "$1[REDACTED]")
      .replace(/(api[_-]?key["']?\s*[:=]\s*["']?)[^"',\s]+/gi, "$1[REDACTED]")
      .replace(/(token["']?\s*[:=]\s*["']?)[^"',\s]+/gi, "$1[REDACTED]")
      .replace(/(cookie["']?\s*[:=]\s*["']?)[^"',\n]+/gi, "$1[REDACTED]");
  }

  if (Array.isArray(value)) {
    return value.map((item) => redactSecrets(item));
  }

  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [key, redactSecrets(item)]),
    );
  }

  return value;
}
