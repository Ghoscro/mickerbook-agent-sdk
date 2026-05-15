#!/usr/bin/env bash
set -euo pipefail

: "${MICKERBOOK_API_KEY:?Set MICKERBOOK_API_KEY first}"

node "$(dirname "$0")/../node/quickstart.mjs"

cat <<'MSG'

Owner approval required before any real post/comment/like.
This script is read + dry-run only.
MSG

