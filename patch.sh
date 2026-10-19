#!/bin/bash
# ONE. セーブページ拡張: 自分のゲームデータからパッチを生成して適用する
cd "$(dirname "$(readlink -f "$0")")" || exit 1
. ./_pyenv.sh
"$PY" -m onepatch install "$@"
pause
