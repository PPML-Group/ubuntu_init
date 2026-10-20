#!/bin/bash
set -e


# 更新apt
sudo apt update
sudo apt install software-properties-common -y
sudo add-apt-repository universe -y
sudo apt update

#安装必要的基本库
sudo apt install build-essential -y
sudo apt install gcc -f -y
sudo apt install make -f -y
sudo apt install g++ -f -y

# 安装git
sudo apt install git -f -y

# 安装doxygen
sudo apt install graphviz -f -y
sudo apt install doxygen -f -y
sudo apt install doxygen-gui -f -y

# 安装openssh并且启动
sudo apt install openssh-server -f -y
sudo service ssh start
sudo systemctl enable ssh

# 安装网络工具
sudo apt install net-tools -f -y

# 安装测速工具
sudo apt install speedtest-cli -f -y

# 安装温度检测工具
sudo apt install psensor -f -y

# 安装其他编译工具
sudo apt install cmake ninja-build pkg-config gdb -y

# 安装下载和终端工具
sudo apt install curl wget ca-certificates unzip zip xz-utils bzip2 jq rsync -y
sudo apt install tmux htop zsh terminator meld -y
sudo apt install ripgrep fd-find nvtop -y
sudo apt install git-lfs -y
git lfs install --skip-repo

# 安装Python工具
sudo apt install python3 python3-dev python3-venv python3-pip python-is-python3 -y

# 安装播放器
sudo apt install vlc ffmpeg -y

# 安装图形库
sudo apt install mesa-utils vulkan-tools libgl1 libglx-mesa0 libegl1 -y
sudo apt install libglfw3 libglfw3-dev libglew-dev libosmesa6-dev -y
sudo apt install libglib2.0-0t64 libsm6 libxext6 libxrender1 -y
sudo apt install libxkbcommon0 libxcb-cursor0 libfuse2t64 -y

# 安装开发库
sudo apt install libvtk9-dev libeigen3-dev libboost-all-dev -y
sudo apt install libasio-dev libtinyxml2-dev libassimp-dev -y
