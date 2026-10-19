#!/bin/bash
# ONE. セーブページ拡張を取り外す（セーブデータは消さない）
cd "$(dirname "$(readlink -f "$0")")" || exit 1
. ./_pyenv.sh
"$PY" -m onepatch uninstall "$@"
pause
