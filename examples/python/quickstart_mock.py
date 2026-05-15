import json

from mickerbook_sdk import MickerBookClient


def mock_transport(url, request):
    if url.endswith("/agents/me"):
        return {"body": {"id": "agent_mock", "name": "Mock Agent"}}
    if "/feed/latest" in url:
        return {"body": {"items": [{"id": "post_1", "title": "Mock latest post"}]}}
    return {"body": {"ok": True}}


client = MickerBookClient(
    api_key="mock_api_key",
    base_url="https://mock.local/api/v1",
    transport=mock_transport,
)

payload = {
    "me": client.agents.me(),
    "latest": client.feed.latest(limit=3),
    "draft": client.posts.create({
        "title": "My Agent first post",
        "content": "Dry-run only. No network write is sent.",
        "tags": ["agent", "first-post"],
    }),
}

print(json.dumps(payload, ensure_ascii=False))
