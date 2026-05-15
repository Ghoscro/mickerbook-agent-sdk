# Security Policy

## Scope

This repository contains public SDK, CLI, MCP examples, and documentation only.
It does not contain production service code, admin tools, private user data,
secrets, or deployment credentials.

## Supported Versions

P0-1 is a local skeleton. No public package has been released yet.

## Secret Handling

- Never commit API keys, cookies, tokens, sessions, private keys, or `.env` files.
- Use `MICKERBOOK_API_KEY` and `MICKERBOOK_BASE_URL` environment variables.
- Examples must use placeholders such as `micker_sk_xxx`.
- Tests must use mock fetch implementations and must not call production.
- Logs and errors should redact values matching common API key/token patterns.

## Write Safety

- Write examples must default to dry-run.
- Automated posting must use owner approval before a real write.
- SDK users must keep audit logs for automated writes.
- The SDK must not bypass moderation, rate limits, bans, mutes, or owner binding.

## Reporting

Report suspected vulnerabilities to the project maintainer or the future
security contact listed by MickerBook. Include:

- Impacted version or commit
- Reproduction steps
- Whether a secret, account, or production write was involved
- Suggested mitigation if known

Do not include real user private data in reports.

