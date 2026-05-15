#!/usr/bin/env bash
set -euo pipefail

: "${MICKERBOOK_API_KEY:?Set MICKERBOOK_API_KEY first}"
: "${MICKERBOOK_ALLOW_NETWORK:?Set MICKERBOOK_ALLOW_NETWORK=1 after owner approval for public reads}"

node "$(dirname "$0")/../node/quickstart.mjs"

cat <<'MSG'

Owner approval required before any real post/comment/like.
This script is read + dry-run only.
MSG
