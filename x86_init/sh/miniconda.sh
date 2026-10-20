#!/bin/bash
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if ((EUID == 0)); then
    echo "请以普通用户安装 Miniconda。" >&2
    exit 1
fi
prefix="$HOME/miniconda3"
if [[ -e $prefix ]]; then
    if [[ ! -x $prefix/bin/conda ]]; then
        echo "${prefix} 已存在但没有可用的conda，请检查目录。" >&2
        exit 1
    fi
    echo "${prefix} 已存在，复用并初始化Shell。"
else
    shopt -s nullglob
    installers=("$script_dir"/../installers/Miniconda3-*-Linux-x86_64.sh)
    if ((${#installers[@]} != 1)); then
        echo "请在 installers/ 中放入一个要安装的 Miniconda Linux x86_64 .sh 文件。" >&2
        exit 1
    fi
    # 交互安装会展示条款，请选择默认路径 ~/miniconda3。
    bash "${installers[0]}" -p "$prefix"
fi
if [[ -x $prefix/bin/conda ]]; then
    "$prefix/bin/conda" init bash zsh
    "$prefix/bin/conda" config --set auto_activate_base false
    echo "Miniconda 已初始化。打开新终端后，为各项目分别创建环境。"
else
    echo "没有在 ${prefix} 检测到 Conda，可能取消安装或选择了其他目录。" >&2
    exit 1
fi
