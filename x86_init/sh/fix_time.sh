#!/bin/bash
set -e

# Windows保持默认本地RTC时使用；Windows已设为UTC则不运行此脚本。
sudo timedatectl set-ntp true
for _ in {1..15}; do
    if [[ $(timedatectl show -p NTPSynchronized --value) == yes ]]; then
        break
    fi
    sleep 2
done
if [[ $(timedatectl show -p NTPSynchronized --value) != yes ]]; then
    echo "等待30秒后网络时间仍未同步，请联网同步完成后重新运行。" >&2
    exit 1
fi

# 用已同步的系统时间写入本地RTC。
sudo timedatectl set-local-rtc 1
timedatectl
