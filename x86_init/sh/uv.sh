#!/bin/bash
set -e
if ((EUID == 0)); then
    echo "请以普通用户安装uv。" >&2
    exit 1
fi

export PATH="$HOME/.local/bin:$PATH"
if command -v uv >/dev/null && uv --version; then
    echo "复用已有uv。"
    exit 0
fi

installer="$(mktemp)"
trap 'rm -f -- "$installer"' EXIT
curl --fail --location --retry 3 --connect-timeout 30 \
    https://astral.sh/uv/install.sh -o "$installer"
UV_INSTALL_DIR="$HOME/.local/bin" UV_NO_MODIFY_PATH=1 sh "$installer"
"$HOME/.local/bin/uv" --version
echo "uv已安装，更新可运行 uv self update。"
