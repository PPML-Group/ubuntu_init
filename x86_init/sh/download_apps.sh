#!/bin/bash
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# 固定使用系统 Python，不要求提前安装 Conda 或额外 Python 包。
exec /usr/bin/python3 "$script_dir/../scripts/download_apps.py" "$@"
