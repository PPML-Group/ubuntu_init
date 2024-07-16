#!/bin/bash

# 安装 Oh My Zsh
sh -c "$(curl -fsSL https://gitee.com/shmhlsy/oh-my-zsh-install.sh/raw/master/install.sh)"

# 克隆 zsh-syntax-highlighting 插件
git clone https://gitee.com/Annihilater/zsh-syntax-highlighting.git ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting

# 克隆 zsh-autosuggestions 插件
git clone https://gitee.com/hailin_cool/zsh-autosuggestions.git ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autosuggestions

# conda-zsh-completion
# git clone https://github.com/esc/conda-zsh-completion $ZSH_CUSTOM/plugins/conda-zsh-completion

# 更新 .zshrc 配置文件以启用新插件
sed -i 's/plugins=(git)/plugins=(git zsh-syntax-highlighting zsh-autosuggestions)/' ~/.zshrc

# 将指定内容插入到 .zshrc
cat << 'EOL' >> ~/.zshrc

# >>> fishros initialize >>>
source /opt/ros/humble/setup.zsh 
# <<< fishros initialize <<<

source /usr/share/colcon_cd/function/colcon_cd.sh
export _colcon_cd_root=/opt/ros/humble/
source /usr/share/colcon_argcomplete/hook/colcon-argcomplete.zsh

complete -o nospace -o default -F _python_argcomplete "ros2"
complete -o nospace -o default -F _python_argcomplete "colcon"

setopt nonomatch
EOL