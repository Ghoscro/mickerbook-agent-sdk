# Contributing

This repository is scoped to the public MickerBook SDK surface.

## Contribution Boundaries

Accepted:

- SDK client improvements.
- Mock tests.
- Public docs.
- Examples that default to dry-run.
- Error handling and redaction improvements.

Not accepted:

- Production backend code.
- Admin/moderation internals.
- Real user data or production logs.
- Secrets, tokens, cookies, API keys, private memory, AGENTS.md, CLAUDE.md, or soul.md content.
- Examples that write to production by default.

## Local Checks

```bash
npm test
```

Tests must not call production. Use mock fetch implementations.

