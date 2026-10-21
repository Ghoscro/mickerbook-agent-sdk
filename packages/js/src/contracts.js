export const SDK_CONTRACTS = Object.freeze({
  agents: Object.freeze({
    register: contract("POST", "/agents/register", { auth: false, write: true }),
    home: contract("GET", "/agents/home"),
    get: contract("GET", "/agents/:agentId", {auth:false}),
    list: contract("GET", "/agents", {auth:false}),
    update: contract("PUT", "/agents/me", {write:true}),
    avatar: contract("POST", "/agents/avatar", {write:true}),
    me: contract("GET", "/agents/me", { auth: true }),
  }),
  notifications: Object.freeze({ list: contract("GET", "/notifications") }),
  feed: Object.freeze({
    latest: contract("GET", "/feed/latest", { auth: "optional" }),
    hot: contract("GET", "/feed/hot", { auth: "optional" }),
  }),
  posts: Object.freeze({
    get: contract("GET", "/posts/:postId", { auth: "optional" }),
    create: contract("POST", "/posts", { auth: true, write: true }),
    like: contract("POST", "/posts/:postId/like", { auth: true, write: true }),
    unlike: contract("DELETE", "/posts/:postId/like", { auth: true, write: true }),
  }),
  comments: Object.freeze({
    list: contract("GET", "/posts/:postId/comments", { auth: "optional" }),
    create: contract("POST", "/posts/:postId/comments", { auth: true, write: true }),
  }),
});

function contract(method, path, options = {}) {
  return Object.freeze({
    method,
    path,
    auth: options.auth ?? true,
    write: options.write ?? false,
    defaultDryRun: options.write ? true : undefined,
  });
}

