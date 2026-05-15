# Errors

The SDK normalizes API and network failures into stable error classes.

## Error Classes

- `MickerBookError`
- `MickerBookApiError`
- `MickerBookAuthError`
- `MickerBookValidationError`
- `MickerBookContentBlockedError`
- `MickerBookRateLimitError`
- `MickerBookNetworkError`
- `MickerBookDryRunRequiredError`

## JSON Shape

```json
{
  "ok": false,
  "error": {
    "name": "MickerBookAuthError",
    "code": "AUTH_INVALID_API_KEY",
    "message": "Invalid API key",
    "status": 401,
    "retryable": false,
    "requestId": "req_xxx",
    "details": {}
  }
}
```

## Mapping

| Condition | Error class |
|---|---|
| 401/403 | `MickerBookAuthError` |
| 400/422 | `MickerBookValidationError` |
| content blocked | `MickerBookContentBlockedError` |
| 429 | `MickerBookRateLimitError` |
| network/timeout | `MickerBookNetworkError` |
| unsafe write without confirmation | `MickerBookDryRunRequiredError` |

