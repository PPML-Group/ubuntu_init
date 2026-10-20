#!/bin/bash
set -euo pipefail
echo "GPU / 驱动状态："
if command -v nvidia-smi >/dev/null; then
    nvidia-smi
else
    echo '没有找到 nvidia-smi；请在 Ubuntu“软件和更新 → 附加驱动”中检查驱动。'
fi
if command -v nvcc >/dev/null; then
    nvcc --version
else
    echo "未检测到 CUDA Toolkit；仅运行预编译 PyTorch 通常不需要 nvcc，编译 CUDA 扩展时按项目选择版本。"
fi
echo "nvidia-smi 显示的 CUDA Version 表示驱动兼容能力，不代表已安装该版本 Toolkit。"
echo "请分别核对项目环境中的 PyTorch、MuJoCo/Warp、Isaac Sim 版本。"
