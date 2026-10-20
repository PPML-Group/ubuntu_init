#!/bin/bash
set -euo pipefail
sudo apt-get update
sudo apt-get install -y software-properties-common
sudo add-apt-repository -y ppa:yannubuntu/boot-repair
sudo apt-get update
sudo apt-get install -y boot-repair
echo "Boot-repair 已安装；修复引导需要另行启动程序。"
