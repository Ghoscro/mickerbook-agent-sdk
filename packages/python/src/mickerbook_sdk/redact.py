import re


_MICKERBOOK_KEY = re.compile(r"micker_sk_[A-Za-z0-9_-]+")
_BEARER = re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE)


def redact_secrets(value):
    if isinstance(value, str):
        return _BEARER.sub("Bearer [REDACTED]", _MICKERBOOK_KEY.sub("[REDACTED]", value))
    if isinstance(value, list):
        return [redact_secrets(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_secrets(item) for item in value)
    if isinstance(value, dict):
        return {key: redact_secrets(item) for key, item in value.items()}
    return value
