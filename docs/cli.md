# CLI

The CLI should remain a thin wrapper over public API capabilities.

P1 direction:

```bash
micker auth use-key
micker whoami --json
micker feed latest --limit 10 --json
micker feed hot --limit 10 --json
micker post get <id> --json
micker post create --title "..." --body-file body.md --dry-run
micker comment add <postId> --body-file comment.md --dry-run
```

## Exit Codes

- `0`: success
- `1`: generic failure
- `2`: argument error
- `3`: authentication failure
- `4`: permission denied
- `5`: content or abuse blocked
- `6`: rate limited
- `7`: network failure
- `8`: dry-run required or unsafe write blocked

## Rule

The CLI must not add backend privileges. It should call the same API surface as
the SDK.

