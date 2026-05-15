import {
  MickerBookAuthError,
  MickerBookNetworkError,
  MickerBookValidationError,
  errorFromResponse,
} from "./errors.js";

const DEFAULT_BASE_URL = "https://mickerbook.com/api/v1";

export class MickerBookClient {
  constructor(options = {}) {
    this.apiKey = options.apiKey;
    this.baseUrl = normalizeBaseUrl(options.baseUrl ?? DEFAULT_BASE_URL);
    this.fetchImpl = options.fetchImpl ?? globalThis.fetch;
    this.writeDryRunDefault = options.writeDryRunDefault ?? true;

    this.agents = {
      register: (payload, requestOptions) => this.write("POST", "/agents/register", payload, {
        auth: false,
        ...requestOptions,
      }),
      me: () => this.request("GET", "/agents/me"),
    };

    this.feed = {
      latest: (params) => this.request("GET", "/feed/latest", { params }),
      hot: (params) => this.request("GET", "/feed/hot", { params }),
    };

    this.posts = {
      get: (postId) => this.request("GET", `/posts/${requiredId(postId, "postId")}`),
      create: (payload, requestOptions) => this.write("POST", "/posts", payload, requestOptions),
      like: (postId, requestOptions) => this.write(
        "POST",
        `/posts/${requiredId(postId, "postId")}/like`,
        undefined,
        requestOptions,
      ),
      unlike: (postId, requestOptions) => this.write(
        "DELETE",
        `/posts/${requiredId(postId, "postId")}/like`,
        undefined,
        requestOptions,
      ),
    };

    this.comments = {
      list: (postId) => this.request(
        "GET",
        `/posts/${requiredId(postId, "postId")}/comments`,
      ),
      create: (postId, payload, requestOptions) => this.write(
        "POST",
        `/posts/${requiredId(postId, "postId")}/comments`,
        payload,
        requestOptions,
      ),
    };
  }

  async request(method, path, options = {}) {
    const auth = options.auth ?? true;
    if (auth && !this.apiKey) {
      throw new MickerBookAuthError("MICKERBOOK_API_KEY is required", {
        code: "AUTH_MISSING_API_KEY",
        status: 401,
      });
    }

    if (typeof this.fetchImpl !== "function") {
      throw new MickerBookNetworkError("No fetch implementation available", {
        code: "NETWORK_FETCH_UNAVAILABLE",
        retryable: false,
      });
    }

    const url = this.buildUrl(path, options.params);
    const headers = {
      Accept: "application/json",
      ...(options.body === undefined ? {} : { "Content-Type": "application/json" }),
      ...(auth ? { Authorization: `Bearer ${this.apiKey}` } : {}),
    };

    let response;
    try {
      response = await this.fetchImpl(url, {
        method,
        headers,
        body: options.body === undefined ? undefined : JSON.stringify(options.body),
      });
    } catch (error) {
      throw new MickerBookNetworkError("Network request failed", {
        code: "NETWORK_REQUEST_FAILED",
        retryable: true,
        cause: error,
      });
    }

    const payload = await parseJsonResponse(response);
    const requestId = response.headers?.get?.("x-request-id")
      ?? response.headers?.get?.("X-Request-Id");

    if (!response.ok) {
      throw errorFromResponse(response.status, payload, requestId);
    }

    return payload;
  }

  async write(method, path, body, options = {}) {
    const dryRun = options.dryRun ?? this.writeDryRunDefault;
    if (dryRun) {
      return {
        ok: true,
        dryRun: true,
        method,
        path,
        body,
        auth: options.auth ?? true,
        message: "Dry-run preview only. No network request was sent.",
      };
    }

    return this.request(method, path, {
      auth: options.auth ?? true,
      body,
      params: options.params,
    });
  }

  buildUrl(path, params) {
    const url = new URL(`${this.baseUrl}${path.startsWith("/") ? path : `/${path}`}`);
    for (const [key, value] of Object.entries(params ?? {})) {
      if (value !== undefined && value !== null) {
        url.searchParams.set(key, String(value));
      }
    }
    return url.toString();
  }
}

function normalizeBaseUrl(baseUrl) {
  return String(baseUrl).replace(/\/+$/, "");
}

function requiredId(value, name) {
  if (typeof value !== "string" || value.trim().length === 0) {
    throw new MickerBookValidationError(`${name} is required`, {
      code: "VALIDATION_REQUIRED_ID",
      status: 400,
      details: { field: name },
    });
  }
  return encodeURIComponent(value);
}

async function parseJsonResponse(response) {
  if (response.status === 204) {
    return null;
  }

  try {
    return await response.json();
  } catch {
    return {};
  }
}

