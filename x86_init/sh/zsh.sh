#!/bin/bash
set -e
if ((EUID == 0)); then
    echo "请以普通用户运行，以配置自己的zsh。" >&2
    exit 1
fi
if ! command -v zsh >/dev/null || ! command -v git >/dev/null; then
    sudo apt update
    sudo apt install zsh git -y
fi

work_dir="$(mktemp -d)"
trap 'rm -rf -- "$work_dir"' EXIT

# 优先使用本地副本，其次Gitee，最后GitHub。
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
clone_repo() {
    local name="$1" destination="$2" marker="$3" mirror="$4" upstream="$5"
    if [[ -f "$destination/$marker" ]]; then
        return
    fi
    if [[ -e "$destination" || -L "$destination" ]]; then
        echo "${destination} 已存在但不完整，请手动检查。" >&2
        exit 1
    fi
    local staging="$work_dir/$name"
    if [[ -f "$script_dir/../github/$name/$marker" ]]; then
        cp -a "$script_dir/../github/$name" "$staging"
    else
        if [[ -z "$mirror" ]] || ! GIT_TERMINAL_PROMPT=0 timeout 90 git clone --depth=1 "$mirror" "$staging"; then
            rm -rf -- "$staging"
            GIT_TERMINAL_PROMPT=0 timeout 90 git clone --depth=1 "$upstream" "$staging"
        fi
    fi
    test -f "$staging/$marker"
    mkdir -p "$(dirname -- "$destination")"
    mv -- "$staging" "$destination"
}

omz="${ZSH:-$HOME/.oh-my-zsh}"
custom="${ZSH_CUSTOM:-$omz/custom}"
clone_repo oh-my-zsh "$omz" oh-my-zsh.sh \
    https://gitee.com/mirrors/oh-my-zsh.git https://github.com/ohmyzsh/ohmyzsh.git
clone_repo zsh-syntax-highlighting "$custom/plugins/zsh-syntax-highlighting" zsh-syntax-highlighting.zsh \
    https://gitee.com/Annihilater/zsh-syntax-highlighting.git https://github.com/zsh-users/zsh-syntax-highlighting.git
clone_repo zsh-autosuggestions "$custom/plugins/zsh-autosuggestions" zsh-autosuggestions.zsh \
    https://gitee.com/hailin_cool/zsh-autosuggestions.git https://github.com/zsh-users/zsh-autosuggestions.git
clone_repo conda-zsh-completion "$custom/plugins/conda-zsh-completion" _conda \
    "" https://github.com/conda-incubator/conda-zsh-completion.git

# 只更新自己的配置段，保留已有配置和Conda初始化。
{
    echo '# >>> ubuntu-init zsh >>>'
    printf 'export ZSH=%q\nexport ZSH_CUSTOM=%q\n' "$omz" "$custom"
    cat <<'EOL'
typeset -U fpath
fpath=("$ZSH_CUSTOM/plugins/conda-zsh-completion" $fpath)
if (( ! $+functions[omz] )); then
    ZSH_THEME="${ZSH_THEME:-robbyrussell}"
    (( $+parameters[plugins] )) || plugins=(git)
    source "$ZSH/oh-my-zsh.sh"
fi
autoload -Uz _conda
compdef _conda conda mamba micromamba
zstyle ':completion:*' use-cache on
(( $+functions[_zsh_autosuggest_start] )) || source "$ZSH_CUSTOM/plugins/zsh-autosuggestions/zsh-autosuggestions.zsh"
(( $+functions[_zsh_highlight] )) || source "$ZSH_CUSTOM/plugins/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh"
typeset -U path
path=("$HOME/.local/bin" $path)
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
[[ -f /usr/share/colcon_cd/function/colcon_cd.sh ]] && source /usr/share/colcon_cd/function/colcon_cd.sh
export _colcon_cd_root=/opt/ros/jazzy
[[ -f /usr/share/colcon_argcomplete/hook/colcon-argcomplete.zsh ]] && source /usr/share/colcon_argcomplete/hook/colcon-argcomplete.zsh
# 在各补全初始化完成后，使用Ubuntu 24.04的argcomplete注册Zsh补全。
if (( $+commands[register-python-argcomplete] )); then
    eval "$(register-python-argcomplete --shell zsh ros2 colcon)"
fi
if [[ -s "${NVM_DIR:-$HOME/.nvm}/nvm.sh" ]] && (( ! $+functions[nvm] )); then
    export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
    source "$NVM_DIR/nvm.sh"
fi
setopt nonomatch
# <<< ubuntu-init zsh <<<
EOL
} > "$work_dir/config.zsh"
/usr/bin/python3 - "$work_dir/config.zsh" <<'PY'
from pathlib import Path
import re
import shutil
import sys
rc = Path.home() / ".zshrc"
text = rc.read_text() if rc.exists() else ""
backup = rc.with_name(".zshrc.ubuntu-init.bak")
if rc.exists() and not backup.exists():
    shutil.copy2(rc, backup)
block = Path(sys.argv[1]).read_text()
pattern = r"(?ms)^# >>> ubuntu-init zsh >>>\n.*?^# <<< ubuntu-init zsh <<<\n?"
# 始终放在鱼香配置之后，避免其补全初始化覆盖这里的注册。
text = re.sub(pattern, "", text).rstrip() + "\n\n" + block
rc.write_text(text)
PY

login_user="$(id -un)"
if [[ $(getent passwd "$login_user" | cut -d: -f7) != "$(command -v zsh)" ]]; then
    sudo chsh -s "$(command -v zsh)" "$login_user"
fi
echo "zsh已配置，请注销并重新登录。"
