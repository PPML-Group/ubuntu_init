#!/bin/bash
set -e
if ((EUID == 0)); then
    echo "请以普通用户运行init.sh，脚本会在需要时调用sudo。" >&2
    exit 1
fi
if (($#)); then
    echo "请在 init.sh 中注释不需要的步骤，或单独运行 sh/ 下的脚本。" >&2
    exit 1
fi
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"

# 安装apt软件
bash sh/apt_install.sh

# 安装deb软件 https://www.todesk.com/linux.html
bash sh/deb_install.sh

# 配置搜狗输入法 https://shurufa.sogou.com/
bash sh/sogou.sh

# 自动安装推荐的驱动
# sudo ubuntu-drivers devices
# sudo ubuntu-drivers autoinstall


# 安装boot-repair
# bash sh/boot-repair.sh

# 安装Docker
# bash sh/docker.sh

# 从fishros安装ROS
bash sh/fishros_ros.sh

# 配置zsh
bash sh/zsh.sh

# 安装本地Zotero包
# bash sh/zotero.sh


# 安装本地Miniconda包
bash sh/miniconda.sh

# 按需安装uv
# bash sh/uv.sh

# 安装本地Blender、MeshLab包
bash sh/blender.sh
# bash sh/meshlab.sh

# 安装TeX Live等工具
# bash sh/research.sh

# 修正Windows双系统切换后的时间
bash sh/fix_time.sh

# 通过npm安装Codex
bash sh/codex.sh

# 初始安装完毕
echo "初始安装完毕."

# 升级软件
# sudo apt upgrade -y
# echo "软件升级完毕."
