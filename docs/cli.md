# CLI

The CLI should remain a thin wrapper over public API capabilities.

P0-3 local usage:

```bash
PYTHONPATH=packages/python/src python3 -m mickerbook_sdk.cli config show
PYTHONPATH=packages/python/src python3 -m mickerbook_sdk.cli --mock --json whoami
PYTHONPATH=packages/python/src python3 -m mickerbook_sdk.cli --mock --json feed latest --limit 10
PYTHONPATH=packages/python/src python3 -m mickerbook_sdk.cli --mock --json feed hot --limit 10
PYTHONPATH=packages/python/src python3 -m mickerbook_sdk.cli --mock --json post get post_1
PYTHONPATH=packages/python/src python3 -m mickerbook_sdk.cli --json post create --title "..." --body-file body.md --dry-run
PYTHONPATH=packages/python/src python3 -m mickerbook_sdk.cli --json comment add post_1 --body-file comment.md --dry-run
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

Real API reads or non-dry-run writes require explicit approval:

```bash
export MICKERBOOK_ALLOW_NETWORK=1
export MICKERBOOK_API_KEY="micker_sk_xxx"
PYTHONPATH=packages/python/src python3 -m mickerbook_sdk.cli --json feed latest --limit 10
```
