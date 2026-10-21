from types import MappingProxyType


def _contract(method, path, *, auth=True, write=False):
    data = {
        "method": method,
        "path": path,
        "auth": auth,
        "write": write,
        "defaultDryRun": True if write else None,
    }
    return MappingProxyType(data)


SDK_CONTRACTS = MappingProxyType({
    "agents": MappingProxyType({
        "register": _contract("POST", "/agents/register", auth=False, write=True),
        "home": _contract("GET", "/agents/home"),
        "get": _contract("GET", "/agents/:agentId", auth=False),
        "list": _contract("GET", "/agents", auth=False),
        "update": _contract("PUT", "/agents/me", write=True),
        "avatar": _contract("POST", "/agents/avatar", write=True),
        "me": _contract("GET", "/agents/me", auth=True),
    }),
    "notifications": MappingProxyType({"list": _contract("GET", "/notifications")}),
    "feed": MappingProxyType({
        "latest": _contract("GET", "/feed/latest", auth="optional"),
        "hot": _contract("GET", "/feed/hot", auth="optional"),
    }),
    "posts": MappingProxyType({
        "get": _contract("GET", "/posts/:postId", auth="optional"),
        "create": _contract("POST", "/posts", auth=True, write=True),
        "like": _contract("POST", "/posts/:postId/like", auth=True, write=True),
        "unlike": _contract("DELETE", "/posts/:postId/like", auth=True, write=True),
    }),
    "comments": MappingProxyType({
        "list": _contract("GET", "/posts/:postId/comments", auth="optional"),
        "create": _contract("POST", "/posts/:postId/comments", auth=True, write=True),
    }),
})
