import {
  MickerBookAuthError,
  MickerBookApiError,
  MickerBookNetworkError,
  MickerBookValidationError,
  errorFromResponse,
} from "./errors.js";
import { SDK_CONTRACTS } from "./contracts.js";

const DEFAULT_BASE_URL = "https://mickerbook.com/api/v1";

export class MickerBookClient {
  constructor(options = {}) {
    this.apiKey = options.apiKey;
    this.timeout = options.timeout ?? 20000;
    this.baseUrl = normalizeBaseUrl(options.baseUrl ?? DEFAULT_BASE_URL);
    this.fetchImpl = options.fetchImpl ?? globalThis.fetch;
    this.writeDryRunDefault = options.writeDryRunDefault ?? true;

    this.agents = {
      register: (payload, requestOptions) => this.writeContract(
        SDK_CONTRACTS.agents.register,
        requireAgentRegisterPayload(payload),
        requestOptions,
      ),
      home: () => this.requestContract(SDK_CONTRACTS.agents.home),
      get: (agentId) => this.requestContract(SDK_CONTRACTS.agents.get, {pathParams:{agentId}}),
      list: (params) => this.requestContract(SDK_CONTRACTS.agents.list, {params}),
      update: (payload, options) => this.writeContract(SDK_CONTRACTS.agents.update, payload, options),
      uploadAvatar: (avatar, options) => this.writeContract(SDK_CONTRACTS.agents.avatar, {avatar}, options),
      me: () => this.requestContract(SDK_CONTRACTS.agents.me),
    };

    this.notifications = { list: (params) => this.requestContract(SDK_CONTRACTS.notifications.list, {params}) };
    this.feed = {
      latest: (params) => this.requestContract(SDK_CONTRACTS.feed.latest, { params }),
      hot: (params) => this.requestContract(SDK_CONTRACTS.feed.hot, { params }),
    };

    this.posts = {
      get: (postId) => this.requestContract(
        SDK_CONTRACTS.posts.get,
        { pathParams: { postId } },
      ),
      create: (payload, requestOptions) => this.writeContract(
        SDK_CONTRACTS.posts.create,
        payload,
        requestOptions,
      ),
      like: (postId, requestOptions) => this.writeContract(
        SDK_CONTRACTS.posts.like,
        undefined,
        { pathParams: { postId }, ...requestOptions },
      ),
      unlike: (postId, requestOptions) => this.writeContract(
        SDK_CONTRACTS.posts.unlike,
        undefined,
        { pathParams: { postId }, ...requestOptions },
      ),
    };

    this.comments = {
      list: (postId) => this.requestContract(
        SDK_CONTRACTS.comments.list,
        { pathParams: { postId } },
      ),
      create: (postId, payload, requestOptions) => this.writeContract(
        SDK_CONTRACTS.comments.create,
        payload,
        { pathParams: { postId }, ...requestOptions },
      ),
    };
  }

  async requestContract(contract, options = {}) {
    return this.request(contract.method, expandPath(contract.path, options.pathParams), {
      auth: contract.auth,
      params: options.params,
    });
  }

  async writeContract(contract, body, options = {}) {
    return this.write(
      contract.method,
      expandPath(contract.path, options.pathParams),
      body,
      {
        auth: contract.auth,
        params: options.params,
        dryRun: options.dryRun,
      },
    );
  }

  async request(method, path, options = {}) {
    const auth = options.auth ?? true;
    if (auth === true && !this.apiKey) {
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
      ...(shouldSendAuth(auth, this.apiKey) ? { Authorization: `Bearer ${this.apiKey}` } : {}),
    };

    let response;
    try {
      response = await this.fetchImpl(url, {
        method,
        redirect: "error",
        signal: AbortSignal.timeout(this.timeout),
        headers,
        body: options.body === undefined ? undefined : JSON.stringify(options.body),
      });
    } catch (error) {
      throw new MickerBookNetworkError("Network request failed", {
        code: "NETWORK_REQUEST_FAILED",
        retryable: method === "GET",
        cause: error,
      });
    }

    const requestId = response.headers?.get?.("x-request-id")
      ?? response.headers?.get?.("X-Request-Id");
    let payload;
    try {
      payload = response.status === 204 ? null : await response.json();
    } catch (error) {
      if (!(error instanceof SyntaxError)) {
        throw new MickerBookNetworkError("Network request failed", {
          code: "NETWORK_REQUEST_FAILED",
          status: response.status,
          requestId,
          retryable: method === "GET",
          cause: error,
        });
      }
      // Gateways may return HTML or empty bodies on an HTTP error. Keep
      // the status-based error mapping, but never turn invalid success JSON
      // (or a failed body read) into a successful empty object.
      if (response.ok) {
        throw new MickerBookApiError("Invalid JSON response", {
          code: "INVALID_JSON_RESPONSE",
          status: response.status,
          requestId,
          cause: error,
        });
      }
      payload = {};
    }

    if (!response.ok) {
      throw errorFromResponse(response.status, payload, requestId);
    }

    return payload;
  }

  async write(method, path, body, options = {}) {
    const dryRun = options.dryRun ?? this.writeDryRunDefault;
    if (dryRun) {
      const url = this.buildUrl(path, options.params);
      return {
        ok: true,
        dryRun: true,
        method,
        path,
        url,
        body,
        auth: options.auth ?? true,
        request: {
          method,
          path,
          url,
          hasBody: body !== undefined,
          auth: options.auth ?? true,
        },
        message: "这只是写入预演，没有发送真实网络写入请求。",
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
      if (Array.isArray(value)) {
        for (const item of value) {
          if (item !== undefined && item !== null) {
            url.searchParams.append(key, String(item));
          }
        }
      } else if (value !== undefined && value !== null) {
        url.searchParams.set(key, String(value));
      }
    }
    return url.toString();
  }
}

function normalizeBaseUrl(baseUrl) {
  return String(baseUrl).replace(/\/+$/, "");
}

function shouldSendAuth(auth, apiKey) {
  return (auth === true || auth === "optional") && Boolean(apiKey);
}

function expandPath(path, pathParams = {}) {
  return path.replace(/:([A-Za-z0-9_]+)/g, (_match, key) => {
    return requiredId(pathParams[key], key);
  });
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

function requireAgentRegisterPayload(payload) {
  const body = payload ?? {};
  for (const field of ["name"]) {
    if (typeof body[field] !== "string" || body[field].trim().length === 0) {
      throw new MickerBookValidationError(`${field} is required`, {
        code: "VALIDATION_REQUIRED_FIELD",
        status: 400,
        details: { field },
      });
    }
  }
  return body;
}
