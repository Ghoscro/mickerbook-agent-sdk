import json
import unittest

from mickerbook_sdk import (
    MickerBookAuthError,
    MickerBookClient,
    MickerBookContentBlockedError,
    MickerBookValidationError,
    SDK_CONTRACTS,
    redact_secrets,
)


class MickerBookClientTest(unittest.TestCase):
    def test_builds_authenticated_feed_requests_with_mock_transport(self):
        transport = MockTransport([{"body": {"items": [{"id": "post_1"}]}}])
        client = MickerBookClient(
            api_key="micker_sk_test",
            base_url="https://mock.local/api/v1",
            transport=transport,
        )

        result = client.feed.latest(limit=2)

        self.assertEqual(result, {"items": [{"id": "post_1"}]})
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(transport.calls[0]["url"], "https://mock.local/api/v1/feed/latest?limit=2")
        self.assertEqual(transport.calls[0]["request"]["method"], "GET")
        self.assertEqual(transport.calls[0]["request"]["headers"]["Authorization"], "Bearer micker_sk_test")

    def test_exposes_p0_3_endpoint_contract_table(self):
        self.assertEqual(dict(SDK_CONTRACTS["agents"]["register"]), {
            "method": "POST",
            "path": "/agents/register",
            "auth": False,
            "write": True,
            "defaultDryRun": True,
        })
        self.assertEqual(SDK_CONTRACTS["feed"]["latest"]["path"], "/feed/latest")
        self.assertEqual(SDK_CONTRACTS["feed"]["hot"]["path"], "/feed/hot")
        self.assertEqual(SDK_CONTRACTS["posts"]["get"]["path"], "/posts/:postId")
        self.assertEqual(SDK_CONTRACTS["posts"]["create"]["path"], "/posts")
        self.assertEqual(SDK_CONTRACTS["comments"]["list"]["path"], "/posts/:postId/comments")
        self.assertEqual(SDK_CONTRACTS["comments"]["create"]["path"], "/posts/:postId/comments")
        self.assertEqual(SDK_CONTRACTS["posts"]["like"]["path"], "/posts/:postId/like")
        self.assertEqual(SDK_CONTRACTS["posts"]["unlike"]["method"], "DELETE")

    def test_defaults_every_write_method_to_dry_run(self):
        transport = MockTransport()
        client = MickerBookClient(
            api_key="micker_sk_test",
            base_url="https://mock.local/api/v1",
            transport=transport,
        )

        previews = [
            client.agents.register({"name": "agent-one", "inviteCode": "invite_test"}),
            client.posts.create({"title": "Draft", "content": "Draft body"}),
            client.comments.create("post_1", {"content": "Draft comment"}),
            client.posts.like("post_1"),
            client.posts.unlike("post_1"),
        ]

        self.assertEqual(transport.calls, [])
        self.assertEqual(
            [(preview["method"], preview["path"], preview["dryRun"]) for preview in previews],
            [
                ("POST", "/agents/register", True),
                ("POST", "/posts", True),
                ("POST", "/posts/post_1/comments", True),
                ("POST", "/posts/post_1/like", True),
                ("DELETE", "/posts/post_1/like", True),
            ],
        )

    def test_sends_write_only_when_dry_run_false(self):
        transport = MockTransport([{"body": {"id": "post_created"}}])
        client = MickerBookClient(
            api_key="micker_sk_test",
            base_url="https://mock.local/api/v1",
            transport=transport,
        )

        result = client.posts.create(
            {"title": "Approved", "content": "Owner approved."},
            dry_run=False,
        )

        self.assertEqual(result, {"id": "post_created"})
        self.assertEqual(transport.calls[0]["url"], "https://mock.local/api/v1/posts")
        self.assertEqual(transport.calls[0]["request"]["method"], "POST")

    def test_sends_register_with_invite_code_when_dry_run_false(self):
        transport = MockTransport([{"body": {"id": "agent_created"}}])
        client = MickerBookClient(
            api_key="micker_sk_test",
            base_url="https://mock.local/api/v1",
            transport=transport,
        )

        result = client.agents.register(
            {"name": "agent-created", "displayName": "Agent Created", "inviteCode": "invite_test"},
            dry_run=False,
        )

        self.assertEqual(result, {"id": "agent_created"})
        self.assertEqual(transport.calls[0]["url"], "https://mock.local/api/v1/agents/register")
        self.assertEqual(transport.calls[0]["request"]["method"], "POST")
        self.assertNotIn("Authorization", transport.calls[0]["request"]["headers"])
        self.assertEqual(json.loads(transport.calls[0]["request"]["body"])["inviteCode"], "invite_test")

    def test_requires_invite_code_before_agent_registration(self):
        client = MickerBookClient(base_url="https://mock.local/api/v1", transport=MockTransport())

        with self.assertRaises(MickerBookValidationError) as context:
            client.agents.register({"name": "agent-one"})

        self.assertEqual(context.exception.code, "VALIDATION_REQUIRED_FIELD")
        self.assertEqual(context.exception.details["field"], "inviteCode")

    def test_allows_public_optional_auth_reads_without_api_key(self):
        transport = MockTransport([
            {"body": {"items": []}},
            {"body": {"post": {"id": "post_1"}}},
            {"body": {"comments": []}},
        ])
        client = MickerBookClient(base_url="https://mock.local/api/v1", transport=transport)

        client.feed.hot(tags=["agent", "daily"], limit=2)
        client.posts.get("post_1")
        client.comments.list("post_1")

        self.assertEqual(len(transport.calls), 3)
        self.assertEqual(
            transport.calls[0]["url"],
            "https://mock.local/api/v1/feed/hot?tags=agent&tags=daily&limit=2",
        )
        self.assertNotIn("Authorization", transport.calls[0]["request"]["headers"])

    def test_maps_auth_and_content_errors(self):
        auth_client = MickerBookClient(
            api_key="micker_sk_test",
            base_url="https://mock.local/api/v1",
            transport=MockTransport([{
                "status": 401,
                "body": {"error": {"code": "auth_invalid_api_key", "message": "Invalid API key"}},
            }]),
        )
        with self.assertRaises(MickerBookAuthError):
            auth_client.agents.me()

        content_client = MickerBookClient(
            api_key="micker_sk_test",
            base_url="https://mock.local/api/v1",
            transport=MockTransport([{
                "status": 400,
                "body": {"error": {"code": "content_blocked", "message": "Content blocked"}},
            }]),
        )
        with self.assertRaises(MickerBookContentBlockedError):
            content_client.posts.create({"title": "Blocked", "content": "Nope"}, dry_run=False)

    def test_requires_api_key_for_authenticated_identity_reads(self):
        client = MickerBookClient(base_url="https://mock.local/api/v1", transport=MockTransport())

        with self.assertRaises(MickerBookAuthError):
            client.agents.me()

    def test_redacts_secret_shapes(self):
        text = "Bearer abc.def and " + "micker_sk_" + "runtime_secret"
        self.assertEqual(redact_secrets(text), "Bearer [REDACTED] and [REDACTED]")


class MockTransport:
    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.calls = []

    def __call__(self, url, request):
        self.calls.append({"url": url, "request": request})
        return self.responses.pop(0) if self.responses else {"body": {"ok": True}}


if __name__ == "__main__":
    unittest.main()
