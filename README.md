# Ubuntu 24.04 初始化

适用于 **Ubuntu 24.04 LTS amd64 桌面版**。ROS 2 通过鱼香 ROS 安装 Jazzy。

使用方式：**在下载方便的电脑上准备安装包 → 将整个 `x86_init/`（包含本地安装包和源码目录）经 U 盘拷到目标电脑 → 安装本地软件，联网安装 apt 工具、依赖和 npm 版 Codex。** 目标电脑无需再次运行下载脚本。也可以用浏览器下载 DEB 后直接放入 `deb/`。

`init.sh` 按顺序调用安装脚本；不需要的步骤直接注释，各 `sh/` 脚本也可单独运行。仓库中的 `jetson_init/` 保留原样，不属于本分支的安装入口。

## 1. 下载常用软件

需要系统 Python 3、curl、dpkg、tar、xz-utils、bzip2。Ubuntu 桌面通常已提供其中大部分，缺少时运行：

```bash
sudo apt-get update
sudo apt-get install curl python3 dpkg tar xz-utils bzip2 ca-certificates

# 在仓库根目录执行；只下载，不安装
bash x86_init/sh/download_apps.sh

# 查看全部软件
bash x86_init/sh/download_apps.sh --list

# 单独选择
bash x86_init/sh/download_apps.sh github-desktop vscode blender
bash x86_init/sh/download_apps.sh sogou todesk

# 可选软件
bash x86_init/sh/download_apps.sh --group research
```

| 软件 ID | 分组 | 来源 / 版本 |
| --- | --- | --- |
| `github-desktop` | default | [Desktop Plus](https://github.com/desktop-plus/desktop-plus)，GitHub Desktop 社区分支，跟随该项目最新稳定版；保留原下载 ID |
| `vscode` | default | [VS Code](https://code.visualstudio.com/) |
| `clash-verge` | default | [Clash Verge Rev](https://github.com/clash-verge-rev/clash-verge-rev) |
| `miniconda` | default | [Anaconda](https://repo.anaconda.com/miniconda/)，base Python 3.11，各项目另建环境 |
| `todesk` | default | [ToDesk](https://www.todesk.com/linux.html)，正式版 |
| `sunlogin` | default | [向日葵个人版](https://sunlogin.oray.com/download/linux)，Linux amd64 DEB |
| `sogou` | default | [搜狗拼音](https://shurufa.sogou.com/linux)，Linux amd64 DEB，使用 Fcitx |
| `blender` | default | [Blender](https://www.blender.org/download/)，跟随官网下载首页的最新稳定版 |
| `nodejs` | default | [Node.js](https://nodejs.org/en/download)，最新 LTS，包含 npm / npx |
| `obsidian` | research | [Obsidian](https://obsidian.md/download) |
| `zotero` | research | [Zotero](https://www.zotero.org/download/) |
| `meshlab` | research | [MeshLab](https://www.meshlab.net/) |
| `chrome` | daily | [Chrome](https://www.google.com/chrome/) |

安装包按类型存放在 `x86_init/` 下的并列目录，均由 Git 忽略，使用 U 盘时需要一起拷贝。每种软件只保留一个要安装的版本，不保留旧包目录。

```text
x86_init/
├── deb/          # DEB安装包
├── archives/     # Blender、Zotero、MeshLab、Node.js
├── installers/   # Miniconda安装脚本
├── github/       # Oh My Zsh及插件源码
├── skills/       # skills备份，不自动安装
└── manifest.json # 下载记录
```

`x86_init/manifest.json` 只供下载器记录版本、来源、文件大小和 SHA256，用于复用与校验，由 Git 忽略；**安装脚本不依赖它**。路径相对于 `x86_init/`。使用 `--output` 时指定的是包含上述分类目录的下载根目录。未下载成功的软件在重试时重新解析地址，同名 `.part` 文件继续用于断点续传。

```bash
# 解析下载地址，不下载、不写缓存
bash x86_init/sh/download_apps.sh --dry-run
# 离线检查缓存完整性
bash x86_init/sh/download_apps.sh --verify
# 显式查询新版本并下载
bash x86_init/sh/download_apps.sh --update
```

重复运行会验证并复用缓存，网络失败可重试，未完成文件保留为 `.part`。上游提供 SHA256 时校验上游摘要；其他包验证格式、DEB 架构和完整压缩内容，并记录本地 SHA256。**本地摘要用于检测后续损坏，不等同于上游签名。**

ToDesk 等网站可能返回浏览器验证页面；脚本会拒绝将其保存成成功的 DEB，并继续其他下载。此时可在官网浏览器中完成验证，将原始文件名的安装包放入 `x86_init/deb/`，再运行 `download_apps.sh todesk` 校验并登记。脚本最后汇总未完成项并返回非零退出码。

ToDesk 的验证也可能受 Python / TLS 运行环境影响；若 Shell 入口失败，且当前 `python3` 是另一套较新的解释器，可尝试 `python3 x86_init/scripts/download_apps.py todesk --update`。下载成功后，Shell 入口可以复用已校验的缓存；不要求为此安装 Conda。

软件来源配置位于 `x86_init/config/apps.json`；Python 实现位于 `x86_init/scripts/download_apps.py` 和 `x86_init/scripts/install_archive.py`，`sh/` 保留 Shell 入口。GitHub 来源可增加 `tag` 固定发布版本；Blender 可增加 `series`（例如 `"5.2"`）限制在某个系列；其他来源可以改成 `resolver: "static"` 并填写 `url`、`version`、可选 `sha256`。

搜狗下载器按官网公开前端逻辑，在传输时生成带时间的下载地址，缓存中保留稳定的来源地址。ToDesk 使用 Python HTTPS 请求并带上官网 Referer，失败时重新完整下载；其他下载使用 curl 断点续传。下载站规则可能变化，仍以安装包校验结果为准。

## 2. 安装

在目标电脑上，用普通用户进入拷贝后的目录。可以直接运行独立脚本，apt 会联网获取软件和缺少的依赖：

```bash
cd x86_init
bash sh/apt_install.sh
bash sh/deb_install.sh
# 搜狗输入法配置
bash sh/sogou.sh
```

也可以先编辑 `x86_init/init.sh`，注释不需要的步骤，再运行：

```bash
bash x86_init/init.sh
```

默认依次执行 `apt_install.sh` → `deb_install.sh` → `sogou.sh` → `fishros_ros.sh` → `zsh.sh` → `miniconda.sh` → `blender.sh` → `fix_time.sh` → `codex.sh`。其他步骤保留为注释；uv、LaTeX、Zotero、MeshLab 和 Docker 均按需安装。Miniconda 安装需要按提示确认条款，鱼香 ROS 需要手动选择菜单。

单独安装或配置时：

```bash
cd x86_init
bash sh/fishros_ros.sh
bash sh/zsh.sh
bash sh/miniconda.sh
bash sh/blender.sh
bash sh/codex.sh
# 按需运行
# bash sh/uv.sh
# bash sh/docker.sh
# bash sh/zotero.sh
# bash sh/meshlab.sh
# bash sh/research.sh
# bash sh/gpu_check.sh
```

`deb_install.sh` 逐个安装 `deb/` 顶层的 DEB，通过 apt 联网补齐依赖。只装某个包时可直接运行 `sudo apt install ./x86_init/deb/文件名.deb`。

apt 软件包直接写在 `sh/apt_install.sh` 和 `sh/research.sh` 的安装命令里，需要增删时编辑对应脚本即可。默认安装 Eigen，不显式安装 `libvtk9-dev` 和 `libboost-all-dev`；需要编译相关项目时再补充。TeX Live 等工具通过 `sh/research.sh` 按需安装。基础安装会启用 OpenSSH 服务；Docker 组权限需要注销后重新登录。

Terminator、ripgrep（`rg`）、fd-find（`fdfind`）、nvtop 均在默认 apt 清单中。

只安装播放器可运行 `sudo apt-get update && sudo apt-get install vlc`。搜狗与 Fcitx5 使用不同的输入法框架；搜狗建议在登录界面选择 **Ubuntu on Xorg**，安装后注销再登录并在 Fcitx 配置中添加搜狗拼音。

Miniconda 和用户目录中的应用请以普通用户运行；已有可用的 `~/miniconda3` 会复用，并初始化 Bash / Zsh、关闭 base 自动激活。Blender 与 Zotero 使用官方压缩包，MeshLab 使用 AppImage，保留下载时的文件名即可识别。Miniconda和压缩包安装入口在发现同一软件有多个版本时会提示整理目录。下载本身不会安装应用、修改代理订阅或配置远程账号。

### zsh

`sh/zsh.sh` 在鱼香 ROS 安装后运行，安装 Oh My Zsh、zsh-autosuggestions、zsh-syntax-highlighting 和 conda-zsh-completion，配置 Cyclone DDS、colcon、`~/.local/bin`、已有 NVM 的加载和默认登录 Shell。ROS 的 `source /opt/ros/jazzy/setup.zsh` 由鱼香写入并保留，不重复添加。首次修改前备份 `.zshrc` 为 `.zshrc.ubuntu-init.bak`，重复运行只更新自己的配置段。Conda 在这一步之后初始化 Bash / Zsh，不自动激活 base，也不在每次开终端时强制退出已激活的环境。`chsh` 只修改后续登录的默认 Shell，不会中断当前 Bash 安装流程。

优先读取 `x86_init/github/` 下的 `oh-my-zsh/`、`zsh-autosuggestions/`、`zsh-syntax-highlighting/`、`conda-zsh-completion/` 本地源码；没有本地副本时，前三项依次尝试 Gitee 镜像和 GitHub 上游，Conda 补全使用 GitHub 上游。已有完整安装直接复用。`github/` 由 Git 忽略，使用 U 盘时与 `deb/` 一起拷贝，安装这些本地源码无需先启动 Clash。

Oh My Zsh 负责初始化补全系统，脚本注册 Conda 补全，无需 `compinit conda`。最后通过 Ubuntu 24.04 的 `register-python-argcomplete --shell zsh ros2 colcon` 注册两者的原生 Zsh 补全，避免此前的 `compinit` 覆盖已有注册，无需再手写 `complete -F`。保留 `setopt nonomatch`。`~/.local/bin` 用于 Blender、本地 Node 和使用 `~/.local` npm 前缀安装的命令。apt 清单中的 `python-is-python3` 为 Conda 补全提供 `python` 命令，不需要激活 base。

### Codex

`sh/codex.sh` 优先复用已有 Node.js ≥22.20 / npm，以同时满足后续 Skills CLI；必要时加载已有 NVM。环境缺失、不可用或版本过低时，使用本地 Node.js LTS 归档补齐并再次检查。Codex 通过 `npm install -g @openai/codex@latest` 联网安装，不再下载独立归档。NVM 沿用自己的全局目录；系统 Node 或本地归档 Node 必要时将 npm 全局目录设为 `~/.local`，无需 `sudo npm`。[官方安装说明](https://learn.chatgpt.com/docs/codex/cli)

安装前确保 npm 下载可用，需要代理时先配置 Clash。首次运行 `codex` 按提示登录；以后在同一 Node 环境中更新：

```bash
npm install -g @openai/codex@latest
```

脚本不迁移账号凭据、会话或原电脑的 Codex 配置。

`sh/codex.sh` 不自动安装或复制 skills，安装清单和更新命令见本文末尾。`x86_init/skills/` 中的本地副本仅作备份，由 Git 忽略，不被安装流程读取，U盘可以不携带它。

## 3. ROS 2 Jazzy

在鱼香菜单中选择“一键安装 ROS → Jazzy → 桌面版”，系统源和 ROS 源按提示配置。菜单编号会变化，脚本不再自动输入固定数字。

脚本指定鱼香使用 Zsh 配置环境，确认 `ros-jazzy-desktop` 已安装后，再安装 desktop-full、MoveIt / Servo / Visual Tools、ros2_control / controllers、Cyclone DDS、xacro、joint-state-publisher-gui、CAN 消息、cv_bridge 和 image_transport。desktop-full 会通过依赖安装感知、仿真和 Gazebo 集成演示包；不额外添加 gz-ros2-control 及其演示包。

新开终端，或使用与你的 Shell 对应的一行：

```bash
# Bash
source /opt/ros/jazzy/setup.bash
# Zsh 改用：source /opt/ros/jazzy/setup.zsh
ros2 run demo_nodes_cpp talker
```

在另一个已加载环境的终端运行 `ros2 run demo_nodes_py listener` 验证通信。

鱼香 ROS 文档见 [上游项目](https://github.com/fishros/install)。

## 4. 项目环境与软件源

项目 Python 依赖按各仓库的说明安装到独立环境中，优先使用其锁文件。PyTorch、JAX、MuJoCo、Warp、Isaac Lab 等按项目要求选择版本。

[OpenPI](https://github.com/Physical-Intelligence/openpi) 和 [GR00T](https://github.com/NVIDIA/Isaac-GR00T) 使用 uv 管理依赖。uv 默认不安装，需要时运行 `sh/uv.sh`，可与 Conda 并存；已有可用的 uv 会复用，否则联网运行官方安装器，将命令放入 `~/.local/bin`，不改写 Shell 配置：

```bash
bash x86_init/sh/uv.sh
# 新开终端后检查；由本脚本下载的独立版可自行更新
uv --version
# uv self update
```

安装方式见 [uv 文档](https://docs.astral.sh/uv/getting-started/installation/)。已有的 `~/.local/bin` PATH 配置可用于 uv。模型和数据集下载可按需使用 [Hugging Face CLI](https://huggingface.co/docs/huggingface_hub/guides/cli)。

以下工具未默认安装，需要时补充：`ccache` 用于 C/C++ 编译缓存，`aria2` 用于大文件下载，`hdf5-tools` 提供 `h5ls` / `h5dump` 数据检查命令。

```bash
sudo apt install ccache aria2 hdf5-tools
```

GPU 驱动按显卡与项目要求安装，可运行 `sh/gpu_check.sh` 检查。CUDA Toolkit 按项目需要选择；编译 CUDA 扩展时才需要额外核对 `nvcc`，安装 PyTorch 本身不包含编译工具链，见 [PyTorch 文档](https://docs.pytorch.org/docs/stable/cpp_extension.html)。

系统 CMake / C++ 工程编译 CUDA 代码时，需要完整 CUDA Toolkit，包括 `nvcc`、头文件及开发库。Conda 中的 CUDA 运行库不等同于完整 Toolkit；若环境内已安装编译工具链，也可以显式指定其路径。系统安装建议从 NVIDIA 源选择固定版本的 `cuda-toolkit-X-Y`，按项目需要设置 `CUDA_HOME`、`PATH` 或 CMake 的 `CUDAToolkit_ROOT`。不要为不同项目统一覆盖全局 `LD_LIBRARY_PATH`。版本同时取决于显卡架构、驱动、项目依赖和宿主 GCC 的支持范围。

需经 U 盘携带 CUDA 时，可使用 NVIDIA 的 Ubuntu 24.04 x86_64 **deb (local)** 安装包：它先注册本地软件源，还需要导入该仓库密钥，再通过 apt 安装指定版本的 Toolkit。应单独存放在 `installers/`，按官网对应版本说明安装，避免放入会批量安装的 `deb/`；基础 apt 依赖仍可联网获取。暂不默认下载某个 CUDA 版本，见 [CUDA Linux 安装指南](https://docs.nvidia.com/cuda/cuda-installation-guide-linux/)。cuDNN、NCCL、TensorRT 是按用途另选的组件；框架已提供运行库时无需再统一安装系统副本。

Ubuntu 24.04 的 ROS Jazzy apt 包使用系统 Python 3.12。运行这些 ROS Python 节点时使用系统解释器；Conda 中不同版本的 Python 不能直接复用其 `rclpy` 二进制模块。需要不同 Python 版本的模型进程可与 ROS 节点分开运行，通过接口通信，见 [ROS Python 环境说明](https://github.com/ros2/ros2_documentation/blob/jazzy/source/How-To-Guides/Using-Python-Packages.rst)。

如需单独更换 Ubuntu 软件源：

```bash
bash x86_init/sh/tsinghua_source.sh
# 或 bash x86_init/sh/aliyun_source.sh
```

换源脚本支持 `ubuntu.sources` 的 DEB822 格式，也支持 `sources.list`；只替换已知 Ubuntu 镜像地址，保留发行版、组件、签名字段和第三方源。首次改动前备份为同路径的 `.old` 文件。

## Windows双系统时间

`init.sh` 默认执行时钟修正，适用于Windows保持默认本地RTC的情况。也可单独运行：

```bash
bash x86_init/sh/fix_time.sh
```

脚本启用网络校时，最多等待30秒，确认已同步后，将硬件时钟设为本地时间。若仍未同步则停止，不写入RTC；联网同步完成后重试。`init.sh` 遇到错误会停止，时钟步骤失败时，后面的 `codex.sh` 尚未执行。Windows已经改为UTC时不要运行；恢复UTC可运行 `sudo timedatectl set-local-rtc 0`。本地RTC对时区切换和夏令时有局限，见 [timedatectl说明](https://manpages.ubuntu.com/manpages/noble/man1/timedatectl.1.html)。

## 检查

```bash
python3 -m unittest discover -s tests -v
bash x86_init/sh/download_apps.sh --verify
```

安装后可检查软件启动、驱动状态和 ROS 通信。

## Skills 安装与维护

装好 Codex 并登录后，可让它按下面清单安装所需 skills。使用 `npx skills@latest` 管理来源和更新；npm 获取管理工具，skills 内容仍从 GitHub 下载，需要相应网络访问。当前 Skills CLI 要求 Node.js ≥ 22.20，本包准备的 Node.js 24 LTS 满足要求。[Skills CLI](https://github.com/vercel-labs/skills)

`-g -a codex` 表示用户级安装，目录是 `~/.agents/skills/`，可跨项目使用；来源记录在 `~/.agents/.skill-lock.json`。本仓库只记录下面 12 个 skills，不包含 `~/.codex/skills/` 中的论文、笔记和 SignalDesk skills。[Codex skills 目录](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills)

| Skill | 用途 | 来源 / 管理方式 |
| --- | --- | --- |
| `find-skills` | 查找其他 skills | [vercel-labs/skills](https://github.com/vercel-labs/skills) |
| `brainstorming` | 实现前梳理需求与设计 | [obra/superpowers](https://github.com/obra/superpowers) |
| `context-compression` | 长任务上下文整理与交接 | [sickn33/antigravity-awesome-skills](https://github.com/sickn33/antigravity-awesome-skills) |
| `git-commit` | 整理提交与提交信息 | [github/awesome-copilot](https://github.com/github/awesome-copilot) |
| `git-pushing` | 提交及推送流程 | [sickn33/antigravity-awesome-skills](https://github.com/sickn33/antigravity-awesome-skills) |
| `github-deep-research` | 深入分析 GitHub 仓库 | [bytedance/deer-flow](https://github.com/bytedance/deer-flow) |
| `github-repo-search` | 搜索和筛选 GitHub 项目 | [yunshu0909/yunshu_skillshub](https://github.com/yunshu0909/yunshu_skillshub/tree/main/coding/github-repo-search)；原路径已迁至 `coding/` |
| `web-search` | 联网检索流程 | [jwynia/agent-skills](https://github.com/jwynia/agent-skills) |
| `image-search` | 搜索配图 | [z0gsh1u/oh-my-writing-skill](https://github.com/z0gsh1u/oh-my-writing-skill) |
| `blender-mcp` | Blender MCP 操作指引 | [vladmdgolam/agent-skills](https://github.com/vladmdgolam/agent-skills) |
| `pdf` | PDF 处理 | [anthropics/skills](https://github.com/anthropics/skills) |
| `pptx` | 演示文稿处理 | [anthropics/skills](https://github.com/anthropics/skills) |

### 通用 skills

按需运行对应命令；`--skill` 只选择指定项，不安装整个仓库的全部 skills。下列命令用于目标电脑，不会由 `init.sh` 自动执行。

```bash
npx skills@latest add vercel-labs/skills -g -a codex --skill find-skills
npx skills@latest add obra/superpowers -g -a codex --skill brainstorming
npx skills@latest add sickn33/antigravity-awesome-skills -g -a codex --skill context-compression git-pushing
npx skills@latest add github/awesome-copilot -g -a codex --skill git-commit
npx skills@latest add bytedance/deer-flow -g -a codex --skill github-deep-research
npx skills@latest add yunshu0909/yunshu_skillshub -g -a codex --skill github-repo-search
npx skills@latest add jwynia/agent-skills -g -a codex --skill web-search
npx skills@latest add z0gsh1u/oh-my-writing-skill -g -a codex --skill image-search
npx skills@latest add vladmdgolam/agent-skills -g -a codex --skill blender-mcp
npx skills@latest add anthropics/skills -g -a codex --skill pdf pptx

# 查看已安装项
npx skills@latest list -g -a codex
# 更新指定项
npx skills@latest update -g pdf pptx
```

`npm update` 不会更新这些 skills；使用 `skills update`。有本地修改的 skill 先保存到自己的 Git 仓库，不要直接用上游更新覆盖。该工具来自 Vercel Labs，不是 Codex 内置的包管理器。[命令说明](https://github.com/vercel-labs/skills/blob/main/docs/commands.md)

Skills 不会自动装好 Blender MCP 服务、外部工具或文档处理依赖，需要按各 skill 的说明另行配置。

可在目标电脑对 Codex 说：

> 阅读本 README 末尾的 Skills 清单，先核对当前来源和可安装名称，再用 Skills CLI 为 Codex 用户级安装清单中的 12 项并列出结果。不要直接复制备份目录，不安装或更新清单以外的 skills。如果本机已有修改过的同名 skill，先保留并说明差异。
