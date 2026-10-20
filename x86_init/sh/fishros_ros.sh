#!/bin/bash
set -euo pipefail
if ((EUID == 0)); then
    echo "请以普通用户运行，以配置自己的ROS环境。" >&2
    exit 1
fi

ros_distro=jazzy
if ! command -v zsh >/dev/null; then
    sudo apt-get update
    sudo apt-get install -y zsh
fi
# 鱼香只配置已存在的rc文件；明确指定后续使用的Zsh。
touch "$HOME/.zshrc"

# 鱼香 ROS 的菜单会随工具更新及系统版本变化，不再写死菜单编号。
# 按提示选择“一键安装 ROS” -> 对应发行版 -> 桌面版。
echo "请在鱼香 ROS 菜单中选择 ROS 2 ${ros_distro} 桌面版。"
installer_dir="$(mktemp -d)"
trap 'rm -rf -- "$installer_dir"' EXIT
wget --timeout=30 --tries=3 https://fishros.com/install -O "$installer_dir/install.sh"
# 下载脚本使用 source、shopt 等 Bash 语法，不能用 Ubuntu 的 sh（dash）执行。
sudo env SHELL="$(command -v zsh)" bash "$installer_dir/install.sh"

# 鱼香工具取消或失败时也可能返回 0；确认目标桌面版确实已安装。
if [[ $(dpkg-query -W -f='${Status}' "ros-${ros_distro}-desktop" 2>/dev/null || true) != "install ok installed" ]]; then
    echo "未检测到已安装的 ros-${ros_distro}-desktop，请重新运行并选择正确版本。" >&2
    exit 1
fi

# ROS 扩展包
packages=(
    desktop-full diagnostic-updater ros-testing
    moveit moveit-servo moveit-visual-tools
    controller-interface controller-manager controller-manager-msgs
    ros2-control ros2-controllers rmw-cyclonedds-cpp
    xacro joint-state-publisher-gui can-msgs
    cv-bridge image-transport robot-state-publisher
)
ros_packages=()
for package in "${packages[@]}"; do
    ros_packages+=("ros-${ros_distro}-${package}")
done
sudo apt-get update
sudo apt-get install -y "${ros_packages[@]}"

echo "ROS 2 ${ros_distro} 及扩展包已安装，请重新打开终端。"
