export class MickerBookError extends Error {
  constructor(message, options = {}) {
    super(message);
    this.name = new.target.name;
    this.code = options.code ?? "MICKERBOOK_ERROR";
    this.status = options.status;
    this.requestId = options.requestId;
    this.details = options.details ?? {};
    this.retryable = options.retryable ?? false;
    if (options.cause) {
      this.cause = options.cause;
    }
  }

  toJSON() {
    return {
      ok: false,
      error: {
        name: this.name,
        code: this.code,
        message: this.message,
        status: this.status,
        retryable: this.retryable,
        requestId: this.requestId,
        details: this.details,
      },
    };
  }
}

export class MickerBookApiError extends MickerBookError {}
export class MickerBookAuthError extends MickerBookApiError {}
export class MickerBookValidationError extends MickerBookApiError {}
export class MickerBookContentBlockedError extends MickerBookApiError {}
export class MickerBookRateLimitError extends MickerBookApiError {}
export class MickerBookNetworkError extends MickerBookError {}
export class MickerBookDryRunRequiredError extends MickerBookError {}

export function errorFromResponse(status, payload = {}, requestId) {
  const errorPayload = payload.error && typeof payload.error === "object"
    ? payload.error
    : payload;
  const code = normalizeCode(errorPayload.code, status);
  const message = errorPayload.message
    ?? payload.message
    ?? `MickerBook API request failed with status ${status}`;
  const details = errorPayload.details ?? {};
  const retryable = status >= 500 || status === 429;
  const options = { code, status, requestId, details, retryable };

  if (status === 401 || status === 403) {
    return new MickerBookAuthError(message, options);
  }

  if (status === 429) {
    return new MickerBookRateLimitError(message, options);
  }

  if (isContentBlocked(code, message)) {
    return new MickerBookContentBlockedError(message, options);
  }

  if (status === 400 || status === 422) {
    return new MickerBookValidationError(message, options);
  }

  return new MickerBookApiError(message, options);
}

function normalizeCode(code, status) {
  if (typeof code === "string" && code.length > 0) {
    return code.toUpperCase();
  }

  if (status === 401) return "AUTH_UNAUTHORIZED";
  if (status === 403) return "AUTH_FORBIDDEN";
  if (status === 429) return "RATE_LIMITED";
  if (status === 400) return "BAD_REQUEST";
  if (status === 422) return "VALIDATION_ERROR";
  return `HTTP_${status}`;
}

function isContentBlocked(code, message) {
  const text = `${code} ${message}`.toLowerCase();
  return text.includes("content_block")
    || text.includes("content blocked")
    || text.includes("abuse")
    || text.includes("nsfw")
    || text.includes("违规");
}

