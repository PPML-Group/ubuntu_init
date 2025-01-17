
# Ubuntu 重装后运行脚本

使用脚本来自动化安装常用的软件，配置工作环境：包括x86和jetson的Ubuntu。

[参考GitHub地址](https://github.com/oyontalas/ubuntu_init)

## 支持系统版本

Ubuntu amd64 桌面版
20.04 LTS，22.04 LTS

## 文件说明

1. `./deb/`目录：通过软件包(.deb)安装的软件，将软件包添加到该目录下
2. `./sh/aliyun_source.sh`：更换阿里云源（推荐，无需图形界面更换源，保证安装过程流畅性）
3. `./sh/apt_install.sh`：安装通过apt安装的软件
4. `./sh/dab_install.sh`：安装在`./deb/`目录下的软件包
5. `./sh/sogou.sh`：卸载ibus并安装搜狗输入法（推荐，需要在“语言支持”中设置键盘输入法系统为fcitx）
6. `./sh/docker.sh`：安装docker官方推荐指令（推荐）
7. `./sh/zotero.sh`：安装zotero,要求可以访问新添加源。如果无法访问，可以使用`./deb/`目录下的软件包安装。
8. `./sh/fishros_ros_docker.sh`：安装fishros的ROS1的docker容器（Ubuntu 20.04版本镜像）。选择容器的原因是ROS的安装和配置比较麻烦，并且ROS会跟Anaconda冲突，使用容器可以避免这些问题。
9. `./sh/boot-repair.sh`：安装boot-repair,这个软件对于双系统（windows+ubuntu）的用户来说非常有用，可以修复grub引导。使用方法自行百度。
10. `./sh/tsinghua_source.sh`：更换清华源（长期未使用，请自行检查是否可用）。

其他文件：其他文件为一些软件的安装脚本，可以根据需要选择是否运行。

## 运行

```shell
git clone https://github.com/PPML-Group/ubuntu_init
cd ubuntu_init/x86_init
bash init.sh
```

## 注意事项

搜狗输入法需要在“语言支持”中设置键盘输入法系统为fcitx4，顺带跟新语言包，重启电脑。然后在右上角的输入法设置中添加搜狗输入法，重启输入法。

## deb建议安装的软件包

暂不提供deb包下载，可以对应软件下载官网或者第三方平台下载deb包。

参考网址

- [Chrome](https://www.google.cn/chrome/)
- [VSCode](https://code.visualstudio.com/#alt-downloads)
- [Edge](https://www.microsoft.com/zh-cn/edge/download)
- [Clash Verge](https://github.com/zzzgydi/clash-verge/releases)
- [NoMachine](https://www.nomachine.com/download)
- [ToDesk](https://www.todesk.com/download.html)
- [搜狗输入法](https://pinyin.sogou.com/linux/?r=pinyin)
- [有道词典](https://fanyi.youdao.com/download-multi)
- [QQ](https://im.qq.com/linuxqq/index.shtml)
- [微信（第三方）](https://archive.ubuntukylin.com/ubuntukylin/pool/partner/weixin_2.1.4_amd64.deb)
- [Electerm](https://electerm.html5beta.com)