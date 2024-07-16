#!/bin/bash

# 安装apt软件
bash sh/apt_install.sh

# 安装deb软件 https://www.todesk.com/linux.html
bash sh/deb_install.sh

# 配置搜狗输入法 https://shurufa.sogou.com/
# bash sh/sogou.sh

# 自动安装推荐的驱动
# sudo ubuntu-drivers devices
# sudo ubuntu-drivers autoinstall


# 安装boot-repair
# bash sh/boot-repair.sh

# 安装Docker
# bash sh/docker.sh

# 从fishros安装Docker
# . sh/fish_docker.sh

# 从fishros安装ROS
. sh/fish_ros.sh

# 从fishros安装ROS的Docker镜像
# . sh/fish_ros_docker.sh

# 安装zotero(国内可以访问添加的源后可安装)
# . sh/zotero.sh


# 初始安装完毕
echo "初始安装完毕."

# 升级软件
# sudo apt upgrade -y
# echo "软件升级完毕."
