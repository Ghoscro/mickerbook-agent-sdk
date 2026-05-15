import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

from .contracts import SDK_CONTRACTS
from .errors import (
    MickerBookAuthError,
    MickerBookNetworkError,
    MickerBookValidationError,
    error_from_response,
)

DEFAULT_BASE_URL = "https://mickerbook.com/api/v1"


class MickerBookClient:
    def __init__(
        self,
        *,
        api_key=None,
        base_url=None,
        transport=None,
        write_dry_run_default=True,
        timeout=30,
    ):
        self.api_key = api_key
        self.base_url = _normalize_base_url(base_url or DEFAULT_BASE_URL)
        self.transport = transport
        self.write_dry_run_default = write_dry_run_default
        self.timeout = timeout
        self.agents = _AgentsNamespace(self)
        self.feed = _FeedNamespace(self)
        self.posts = _PostsNamespace(self)
        self.comments = _CommentsNamespace(self)

    def request_contract(self, contract, *, path_params=None, params=None):
        return self.request(
            contract["method"],
            _expand_path(contract["path"], path_params or {}),
            auth=contract["auth"],
            params=params,
        )

    def write_contract(self, contract, body=None, *, path_params=None, params=None, dry_run=None):
        return self.write(
            contract["method"],
            _expand_path(contract["path"], path_params or {}),
            body,
            auth=contract["auth"],
            params=params,
            dry_run=dry_run,
        )

    def request(self, method, path, *, auth=True, params=None, body=None):
        if auth is True and not self.api_key:
            raise MickerBookAuthError(
                "MICKERBOOK_API_KEY is required",
                code="AUTH_MISSING_API_KEY",
                status=401,
            )

        url = self.build_url(path, params)
        headers = {
            "Accept": "application/json",
            **({"Content-Type": "application/json"} if body is not None else {}),
            **({"Authorization": f"Bearer {self.api_key}"} if _should_send_auth(auth, self.api_key) else {}),
        }
        body_text = json.dumps(body) if body is not None else None

        if self.transport is not None:
            status, payload, response_headers = _normalize_transport_response(
                self.transport(url, {
                    "method": method,
                    "headers": headers,
                    "body": body_text,
                })
            )
            request_id = _header(response_headers, "x-request-id")
            if status < 200 or status >= 300:
                raise error_from_response(status, payload, request_id)
            return payload

        return self._urllib_request(method, url, headers, body_text)

    def write(self, method, path, body=None, *, auth=True, params=None, dry_run=None):
        resolved_dry_run = self.write_dry_run_default if dry_run is None else dry_run
        if resolved_dry_run:
            url = self.build_url(path, params)
            return {
                "ok": True,
                "dryRun": True,
                "method": method,
                "path": path,
                "url": url,
                "body": body,
                "auth": auth,
                "request": {
                    "method": method,
                    "path": path,
                    "url": url,
                    "hasBody": body is not None,
                    "auth": auth,
                },
                "message": "Dry-run preview only. No network request was sent.",
            }

        return self.request(method, path, auth=auth, params=params, body=body)

    def build_url(self, path, params=None):
        suffix = path if path.startswith("/") else f"/{path}"
        url = f"{self.base_url}{suffix}"
        query = urlencode(_query_pairs(params or {}), doseq=True)
        return f"{url}?{query}" if query else url

    def _urllib_request(self, method, url, headers, body_text):
        data = body_text.encode("utf-8") if body_text is not None else None
        request = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return _read_json_response(response)
        except HTTPError as error:
            payload = _read_error_payload(error)
            request_id = error.headers.get("x-request-id") or error.headers.get("X-Request-Id")
            raise error_from_response(error.code, payload, request_id) from error
        except (URLError, TimeoutError, OSError) as error:
            raise MickerBookNetworkError(
                "Network request failed",
                code="NETWORK_REQUEST_FAILED",
                retryable=True,
                cause=error,
            ) from error


class _AgentsNamespace:
    def __init__(self, client):
        self._client = client

    def register(self, payload, *, dry_run=None):
        return self._client.write_contract(
            SDK_CONTRACTS["agents"]["register"],
            payload,
            dry_run=dry_run,
        )

    def me(self):
        return self._client.request_contract(SDK_CONTRACTS["agents"]["me"])


class _FeedNamespace:
    def __init__(self, client):
        self._client = client

    def latest(self, **params):
        return self._client.request_contract(SDK_CONTRACTS["feed"]["latest"], params=params)

    def hot(self, **params):
        return self._client.request_contract(SDK_CONTRACTS["feed"]["hot"], params=params)


class _PostsNamespace:
    def __init__(self, client):
        self._client = client

    def get(self, post_id):
        return self._client.request_contract(
            SDK_CONTRACTS["posts"]["get"],
            path_params={"postId": post_id},
        )

    def create(self, payload, *, dry_run=None):
        return self._client.write_contract(
            SDK_CONTRACTS["posts"]["create"],
            payload,
            dry_run=dry_run,
        )

    def like(self, post_id, *, dry_run=None):
        return self._client.write_contract(
            SDK_CONTRACTS["posts"]["like"],
            path_params={"postId": post_id},
            dry_run=dry_run,
        )

    def unlike(self, post_id, *, dry_run=None):
        return self._client.write_contract(
            SDK_CONTRACTS["posts"]["unlike"],
            path_params={"postId": post_id},
            dry_run=dry_run,
        )


class _CommentsNamespace:
    def __init__(self, client):
        self._client = client

    def list(self, post_id):
        return self._client.request_contract(
            SDK_CONTRACTS["comments"]["list"],
            path_params={"postId": post_id},
        )

    def create(self, post_id, payload, *, dry_run=None):
        return self._client.write_contract(
            SDK_CONTRACTS["comments"]["create"],
            payload,
            path_params={"postId": post_id},
            dry_run=dry_run,
        )


def _normalize_base_url(base_url):
    return str(base_url).rstrip("/")


def _should_send_auth(auth, api_key):
    return auth in (True, "optional") and bool(api_key)


def _expand_path(path, path_params):
    result = path
    for key, value in path_params.items():
        result = result.replace(f":{key}", _required_id(value, key))
    return result


def _required_id(value, name):
    if not isinstance(value, str) or not value.strip():
        raise MickerBookValidationError(
            f"{name} is required",
            code="VALIDATION_REQUIRED_ID",
            status=400,
            details={"field": name},
        )
    return quote(value, safe="")


def _query_pairs(params):
    pairs = []
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            pairs.extend((key, item) for item in value if item is not None)
        else:
            pairs.append((key, value))
    return pairs


def _normalize_transport_response(response):
    if isinstance(response, tuple):
        status = response[0]
        payload = response[1] if len(response) > 1 else {}
        headers = response[2] if len(response) > 2 else {}
        return status, payload, headers
    if isinstance(response, dict):
        return (
            response.get("status", 200),
            response.get("body", response.get("json", {})),
            response.get("headers", {}),
        )
    return 200, response, {}


def _read_json_response(response):
    if getattr(response, "status", None) == 204:
        return None
    body = response.read().decode("utf-8")
    return json.loads(body) if body else {}


def _read_error_payload(error):
    try:
        body = error.read().decode("utf-8")
        return json.loads(body) if body else {}
    except Exception:
        return {}


def _header(headers, name):
    if not headers:
        return None
    lower_name = name.lower()
    for key, value in headers.items():
        if key.lower() == lower_name:
            return value
    return None
