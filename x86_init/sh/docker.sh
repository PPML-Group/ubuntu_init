#!/bin/bash
set -eo pipefail

# Add Docker's official GPG key:
sudo apt-get update
sudo apt-get install ca-certificates curl gnupg -f -y
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --batch --yes --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update

# 安装
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -f -y

# 非root启动
sudo groupadd -f docker
sudo usermod -aG docker "$USER"

# 开机自启
sudo systemctl enable --now docker.service
sudo systemctl enable --now containerd.service

echo "注销并重新登录后应用docker组权限."
