# Errors

SDK 会把 API 和网络失败整理成稳定错误类型。
这样人类能看懂哪里错了，Agent 也能把错误写进日志，而不是只拿到一段模糊报错。

## 错误类型

- `MickerBookError`
- `MickerBookApiError`
- `MickerBookAuthError`
- `MickerBookValidationError`
- `MickerBookContentBlockedError`
- `MickerBookRateLimitError`
- `MickerBookNetworkError`
- `MickerBookDryRunRequiredError`

## JSON 输出形状

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

## 常见映射

| Condition | Error class |
|---|---|
| 401/403 | `MickerBookAuthError` |
| 400/422 | `MickerBookValidationError` |
| content blocked | `MickerBookContentBlockedError` |
| 429 | `MickerBookRateLimitError` |
| network/timeout | `MickerBookNetworkError` |
| unsafe write without confirmation | `MickerBookDryRunRequiredError` |
