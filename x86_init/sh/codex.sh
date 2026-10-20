#!/bin/bash
set -e
if ((EUID == 0)); then
    echo "请以普通用户安装Codex。" >&2
    exit 1
fi
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# 同时满足Codex和后续Skills CLI的运行环境。
node_ready() {
    command -v node >/dev/null && command -v npm >/dev/null &&
        node -e 'const [major, minor] = process.versions.node.split(".").map(Number);
                 process.exit(major > 22 || (major === 22 && minor >= 20) ? 0 : 1)' &&
        npm --version >/dev/null
}

# 非交互Shell可能没有加载已有的NVM。
if ! node_ready; then
    export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
    if [[ -s "$NVM_DIR/nvm.sh" ]]; then
        # shellcheck source=/dev/null
        if ! source "$NVM_DIR/nvm.sh"; then
            echo "NVM加载失败，尝试本地Node.js包。" >&2
        fi
    fi
fi
if ! node_ready; then
    export PATH="$HOME/.local/bin:$PATH"
    if ! node_ready; then
        /usr/bin/python3 "$script_dir/../scripts/install_archive.py" nodejs
        hash -r
    fi
fi
if ! node_ready; then
    echo "需要Node.js >=22.20及可用的npm；请升级已有环境或更换archives/中的Node.js LTS包。" >&2
    exit 1
fi

# NVM沿用自己的全局目录；系统Node和本地归档Node使用用户可写目录。
npm_prefix="$(npm prefix -g)"
if [[ ! -w "$npm_prefix" || "$npm_prefix" == "$HOME/.local/opt/nodejs-"* ]]; then
    npm config set prefix "$HOME/.local"
    npm_prefix="$HOME/.local"
fi
npm install -g @openai/codex@latest
"$npm_prefix/bin/codex" --version

echo "Codex已安装。首次运行codex按提示登录；以后用 npm install -g @openai/codex@latest 更新。"
echo "Skills按README末尾清单安装和更新。"
