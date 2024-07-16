#!/bin/bash


# 更新apt
sudo apt update

#安装必要的基本库
sudo apt-get install -y build-essential curl wget 

# 安装git
sudo apt install git -f -y

# 安装doxygen
sudo apt install zsh -f -y

# 安装openssh并且启动
sudo apt install openssh-server -f -y
# sudo service ssh start
# sudo systemctl enable ssh

# 安装网络工具
sudo apt install net-tools -f -y

# 安装测速工具
sudo apt install speedtest-cli -f -y

# 安装温度检测工具
sudo apt install psensor -f -y

# 安装terminator
sudo apt install terminator -f -y

