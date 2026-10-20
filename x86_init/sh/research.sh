#!/bin/bash
set -euo pipefail
sudo apt-get update
sudo apt-get install -y software-properties-common
sudo add-apt-repository -y universe
sudo apt-get update
# TeX Live、字体及相关工具
sudo apt-get install -y \
    latexmk texlive-latex-extra texlive-science texlive-fonts-recommended \
    texlive-xetex texlive-lang-chinese biber fonts-noto-cjk \
    poppler-utils ghostscript inkscape pandoc
echo "软件已安装。"
