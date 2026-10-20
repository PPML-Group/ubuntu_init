#!/bin/bash
set -e
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
shopt -s nullglob
files=("$script_dir"/../deb/*.deb)

if ((${#files[@]} == 0)); then
    echo "deb/ 中没有 .deb 文件。"
    exit 0
fi

# 安装所有deb和依赖
sudo apt update
for file in "${files[@]}"
do
    echo "------------------正在安装$file...------------------"
    sudo apt install "$file" -y
    echo "------------------$file安装完毕.------------------"
done

echo "已经安装所有同文件夹的deb和依赖."
