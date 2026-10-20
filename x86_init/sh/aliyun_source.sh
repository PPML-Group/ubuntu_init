#!/bin/bash
set -e

# Ubuntu 24.04默认使用ubuntu.sources
source_file=/etc/apt/sources.list.d/ubuntu.sources
if [ ! -f "$source_file" ]; then
    source_file=/etc/apt/sources.list
fi
if [ ! -f "$source_file" ]; then
    echo "没有找到Ubuntu源文件."
    exit 1
fi

# 备份源
if [ ! -f "${source_file}.old" ]; then
    sudo cp -p "$source_file" "${source_file}.old"
    echo "已经备份源到${source_file}.old."
fi

# 更换Ubuntu镜像地址，保留其他配置
pattern='https?://(([[:alnum:]-]+\.)?archive\.ubuntu\.com|security\.ubuntu\.com|mirrors?\.tuna\.tsinghua\.edu\.cn|mirrors\.aliyun\.com)/ubuntu/?'
if ! grep -Eq "$pattern" "$source_file"; then
    echo "没有找到已知Ubuntu镜像地址，请手动检查."
    exit 1
fi
sudo sed -E -i "s@${pattern}@https://mirrors.aliyun.com/ubuntu/@g" "$source_file"
echo "已经使用阿里云源."

# 更新源
sudo apt update
echo "已经更新源."
