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

## 响应正文异常

JavaScript SDK 在收到响应头后仍会等待完整正文。正文超时、中断或读取失败会抛出
`MickerBookNetworkError`（`NETWORK_REQUEST_FAILED`），保留可用的状态码和请求 ID；
SDK 不会自动重试请求。网络失败的 `retryable` 仅对 GET 为真，不能据此重放写入。

JavaScript 的成功响应若不是有效 JSON（含空正文，204 除外），会抛出
`MickerBookApiError`（`INVALID_JSON_RESPONSE`），不再返回成功的空对象；204 仍返回 `null`。

HTTP 错误响应即使包含 HTML 或非对象 JSON，JS / Python SDK 也会按 HTTP 状态映射为
SDK 错误并保留请求 ID。无法识别的错误消息使用通用说明，不将原始响应正文放进错误消息。
