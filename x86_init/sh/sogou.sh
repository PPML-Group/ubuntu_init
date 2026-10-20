#!/bin/bash
set -e

if ((EUID == 0)); then
    echo "请以普通用户运行，以设置自己的输入法。" >&2
    exit 1
fi

# 安装fcitx
sudo apt update
sudo apt install fcitx fcitx-config-gtk fcitx-frontend-gtk3 fcitx-frontend-qt5 im-config -y

# 安装搜狗输入法依赖
sudo apt install libqt5qml5 libqt5quick5 libqt5quickwidgets5 qml-module-qtquick2 -y
sudo apt install libgsettings-qt1 -y
echo "已经安装搜狗输入法依赖."

# 将键盘输入法系统改为fcitx
im-config -n fcitx
echo "已经将键盘输入法系统改为fcitx，请注销并重新登录."
