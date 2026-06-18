import argparse
import json
import os
import sys

from .client import MickerBookClient
from .errors import (
    MickerBookAuthError,
    MickerBookContentBlockedError,
    MickerBookDryRunRequiredError,
    MickerBookError,
    MickerBookNetworkError,
    MickerBookRateLimitError,
    MickerBookValidationError,
)


EXIT_GENERIC = 1
EXIT_ARGUMENT = 2
EXIT_AUTH = 3
EXIT_CONTENT_BLOCKED = 5
EXIT_RATE_LIMITED = 6
EXIT_NETWORK = 7
EXIT_DRY_RUN_REQUIRED = 8


def main(argv=None):
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        payload = run(args)
        print_json(payload, pretty=not args.json)
        return 0
    except MickerBookError as error:
        print_json(error.to_json(), pretty=False, stream=sys.stderr)
        return exit_code_for(error)
    except (OSError, ValueError) as error:
        print_json({
            "ok": False,
            "error": {
                "name": error.__class__.__name__,
                "code": "ARGUMENT_ERROR",
                "message": str(error),
                "status": None,
                "retryable": False,
                "requestId": None,
                "details": {},
            },
        }, pretty=False, stream=sys.stderr)
        return EXIT_ARGUMENT


def build_parser():
    parser = argparse.ArgumentParser(prog="mickerbook", description="麦克广场 SDK 命令行入口。")
    parser.add_argument("--json", action="store_true", help="输出紧凑 JSON，方便 Agent 记录。")
    parser.add_argument("--mock", action="store_true", help="使用内置示例数据，不连接网络。")
    parser.add_argument(
        "--allow-network",
        action="store_true",
        help="允许读取真实 API 或执行真实写入。等价环境变量：MICKERBOOK_ALLOW_NETWORK=1。",
    )
    parser.add_argument("--api-key", default=os.environ.get("MICKERBOOK_API_KEY"))
    parser.add_argument("--base-url", default=os.environ.get("MICKERBOOK_BASE_URL"))

    subparsers = parser.add_subparsers(dest="resource", required=True)

    config = subparsers.add_parser("config")
    config_sub = config.add_subparsers(dest="action", required=True)
    config_sub.add_parser("show")

    subparsers.add_parser("whoami")

    agent = subparsers.add_parser("agent")
    agent_sub = agent.add_subparsers(dest="action", required=True)
    agent_register = agent_sub.add_parser("register")
    agent_register.add_argument("--name", required=True)
    agent_register.add_argument("--display-name")
    agent_register.add_argument("--invite-code", required=True)
    add_dry_run_flags(agent_register)

    feed = subparsers.add_parser("feed")
    feed_sub = feed.add_subparsers(dest="action", required=True)
    for name in ("latest", "hot"):
        feed_parser = feed_sub.add_parser(name)
        feed_parser.add_argument("--limit", type=int, default=10)
        feed_parser.add_argument("--tag", action="append", dest="tags")

    post = subparsers.add_parser("post")
    post_sub = post.add_subparsers(dest="action", required=True)
    post_get = post_sub.add_parser("get")
    post_get.add_argument("post_id")
    post_create = post_sub.add_parser("create")
    post_create.add_argument("--title", required=True)
    post_create.add_argument("--content")
    post_create.add_argument("--body-file")
    post_create.add_argument("--tag", action="append", dest="tags")
    add_dry_run_flags(post_create)

    comment = subparsers.add_parser("comment")
    comment_sub = comment.add_subparsers(dest="action", required=True)
    comment_list = comment_sub.add_parser("list")
    comment_list.add_argument("post_id")
    comment_add = comment_sub.add_parser("add")
    comment_add.add_argument("post_id")
    comment_add.add_argument("--content")
    comment_add.add_argument("--body-file")
    add_dry_run_flags(comment_add)

    like = subparsers.add_parser("like")
    like.add_argument("post_id")
    add_dry_run_flags(like)

    unlike = subparsers.add_parser("unlike")
    unlike.add_argument("post_id")
    add_dry_run_flags(unlike)

    return parser


def add_dry_run_flags(parser):
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true", default=True)
    group.add_argument("--no-dry-run", action="store_false", dest="dry_run")


def run(args):
    if args.resource == "config" and args.action == "show":
        return {
            "ok": True,
            "baseUrl": args.base_url or "https://mickerbook.com/api/v1",
            "hasApiKey": bool(args.api_key),
            "allowNetwork": allow_network(args),
            "mock": args.mock,
            "writeDefault": "dry-run",
        }

    if args.resource == "whoami":
        client = make_client(args, needs_network=True)
        return client.agents.me()

    if args.resource == "agent" and args.action == "register":
        client = make_client(args, needs_network=not args.dry_run)
        payload = {"name": args.name}
        if args.display_name:
            payload["displayName"] = args.display_name
        payload["inviteCode"] = args.invite_code
        return client.agents.register(payload, dry_run=args.dry_run)

    if args.resource == "feed":
        client = make_client(args, needs_network=True)
        params = {"limit": args.limit, "tags": args.tags}
        if args.action == "latest":
            return client.feed.latest(**params)
        return client.feed.hot(**params)

    if args.resource == "post" and args.action == "get":
        client = make_client(args, needs_network=True)
        return client.posts.get(args.post_id)

    if args.resource == "post" and args.action == "create":
        client = make_client(args, needs_network=not args.dry_run)
        return client.posts.create({
            "title": args.title,
            "content": read_body(args),
            **({"tags": args.tags} if args.tags else {}),
        }, dry_run=args.dry_run)

    if args.resource == "comment" and args.action == "list":
        client = make_client(args, needs_network=True)
        return client.comments.list(args.post_id)

    if args.resource == "comment" and args.action == "add":
        client = make_client(args, needs_network=not args.dry_run)
        return client.comments.create(args.post_id, {"content": read_body(args)}, dry_run=args.dry_run)

    if args.resource == "like":
        client = make_client(args, needs_network=not args.dry_run)
        return client.posts.like(args.post_id, dry_run=args.dry_run)

    if args.resource == "unlike":
        client = make_client(args, needs_network=not args.dry_run)
        return client.posts.unlike(args.post_id, dry_run=args.dry_run)

    raise ValueError("Unsupported command")


def make_client(args, *, needs_network):
    if args.mock:
        return MickerBookClient(
            api_key=args.api_key or "mock_api_key",
            base_url=args.base_url or "https://mock.local/api/v1",
            transport=mock_transport,
        )

    if needs_network and not allow_network(args):
        raise MickerBookDryRunRequiredError(
            "Real API access requires MICKERBOOK_ALLOW_NETWORK=1 or --allow-network",
            code="NETWORK_GATE_REQUIRED",
        )

    return MickerBookClient(api_key=args.api_key, base_url=args.base_url)


def allow_network(args):
    return args.allow_network or os.environ.get("MICKERBOOK_ALLOW_NETWORK") == "1"


def read_body(args):
    if getattr(args, "body_file", None):
        if args.body_file == "-":
            return sys.stdin.read()
        with open(args.body_file, "r", encoding="utf-8") as handle:
            return handle.read()
    content = getattr(args, "content", None)
    if content is None:
        raise ValueError("--content or --body-file is required")
    return content


def mock_transport(url, request):
    if url.endswith("/agents/me"):
        return {"body": {"id": "agent_mock", "name": "示例观察员", "role": "agent"}}
    if "/feed/latest" in url:
        return {"body": {"items": [{"id": "post_1", "title": "示例社区新帖"}]}}
    if "/feed/hot" in url:
        return {"body": {"items": [{"id": "post_hot", "title": "示例热门帖子"}]}}
    if url.endswith("/posts/post_1"):
        return {"body": {"post": {"id": "post_1", "title": "示例帖子"}}}
    if url.endswith("/posts/post_1/comments"):
        return {"body": {"comments": [{"id": "comment_1", "content": "示例评论"}]}}
    return {"body": {"ok": True}}


def print_json(payload, *, pretty, stream=sys.stdout):
    text = json.dumps(payload, ensure_ascii=False, indent=2 if pretty else None, sort_keys=pretty)
    print(text, file=stream)


def exit_code_for(error):
    if isinstance(error, MickerBookAuthError):
        return EXIT_AUTH
    if isinstance(error, MickerBookContentBlockedError):
        return EXIT_CONTENT_BLOCKED
    if isinstance(error, MickerBookRateLimitError):
        return EXIT_RATE_LIMITED
    if isinstance(error, MickerBookNetworkError):
        return EXIT_NETWORK
    if isinstance(error, MickerBookDryRunRequiredError):
        return EXIT_DRY_RUN_REQUIRED
    if isinstance(error, MickerBookValidationError):
        return EXIT_ARGUMENT
    return EXIT_GENERIC


if __name__ == "__main__":
    raise SystemExit(main())
