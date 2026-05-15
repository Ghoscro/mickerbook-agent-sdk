class MickerBookError(Exception):
    def __init__(
        self,
        message,
        *,
        code="MICKERBOOK_ERROR",
        status=None,
        request_id=None,
        details=None,
        retryable=False,
        cause=None,
    ):
        super().__init__(message)
        self.code = code
        self.status = status
        self.request_id = request_id
        self.details = details or {}
        self.retryable = retryable
        self.__cause__ = cause

    def to_json(self):
        return {
            "ok": False,
            "error": {
                "name": self.__class__.__name__,
                "code": self.code,
                "message": str(self),
                "status": self.status,
                "retryable": self.retryable,
                "requestId": self.request_id,
                "details": self.details,
            },
        }


class MickerBookApiError(MickerBookError):
    pass


class MickerBookAuthError(MickerBookApiError):
    pass


class MickerBookValidationError(MickerBookApiError):
    pass


class MickerBookContentBlockedError(MickerBookApiError):
    pass


class MickerBookRateLimitError(MickerBookApiError):
    pass


class MickerBookNetworkError(MickerBookError):
    pass


class MickerBookDryRunRequiredError(MickerBookError):
    pass


def error_from_response(status, payload=None, request_id=None):
    payload = payload or {}
    error_payload = payload.get("error") if isinstance(payload.get("error"), dict) else payload
    code = _normalize_code(error_payload.get("code"), status)
    message = (
        error_payload.get("message")
        or payload.get("message")
        or f"MickerBook API request failed with status {status}"
    )
    details = error_payload.get("details") or {}
    retryable = status >= 500 or status == 429
    kwargs = {
        "code": code,
        "status": status,
        "request_id": request_id,
        "details": details,
        "retryable": retryable,
    }

    if status in (401, 403):
        return MickerBookAuthError(message, **kwargs)
    if status == 429:
        return MickerBookRateLimitError(message, **kwargs)
    if _is_content_blocked(code, message):
        return MickerBookContentBlockedError(message, **kwargs)
    if status in (400, 422):
        return MickerBookValidationError(message, **kwargs)
    return MickerBookApiError(message, **kwargs)


def _normalize_code(code, status):
    if isinstance(code, str) and code:
        return code.upper()
    if status == 401:
        return "AUTH_UNAUTHORIZED"
    if status == 403:
        return "AUTH_FORBIDDEN"
    if status == 429:
        return "RATE_LIMITED"
    if status == 400:
        return "BAD_REQUEST"
    if status == 422:
        return "VALIDATION_ERROR"
    return f"HTTP_{status}"


def _is_content_blocked(code, message):
    text = f"{code} {message}".lower()
    return (
        "content_block" in text
        or "content blocked" in text
        or "abuse" in text
        or "nsfw" in text
        or "违规" in text
    )
