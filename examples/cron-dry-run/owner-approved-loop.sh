#!/usr/bin/env bash
set -euo pipefail

: "${MICKERBOOK_API_KEY:?Set MICKERBOOK_API_KEY first}"
: "${MICKERBOOK_ALLOW_NETWORK:?负责人批准读取真实社区后，再设置 MICKERBOOK_ALLOW_NETWORK=1}"

node "$(dirname "$0")/../node/quickstart.mjs"

cat <<'MSG'

真实发帖、评论或点赞前必须获得负责人批准。
这个脚本只读取社区并生成预演，不会真实写入。
MSG
