#!/usr/bin/env python3
"""Install local application archives into ~/.local."""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def install(name):
    if os.geteuid() == 0:
        raise ValueError("请使用普通用户运行")
    patterns = {
        "blender": "blender-*-linux-x64.tar.xz",
        "zotero": "Zotero-*_linux-x86_64.tar.*",
        "meshlab": "MeshLab*-linux_x86_64.AppImage",
        "nodejs": "node-v*-linux-x64.tar.xz",
    }
    candidates = list((ROOT / "archives").glob(patterns[name]))
    if len(candidates) != 1 or not candidates[0].is_file():
        raise ValueError(f"请在 archives/ 中放入一个要安装的 {patterns[name]} 文件")
    archive_path = candidates[0]
    match = re.search(r"\d+(?:\.\d+)+", archive_path.name)
    if not match:
        raise ValueError(f"文件名中找不到版本号：{archive_path.name}")
    local = Path.home() / ".local"
    apps = local / "opt"
    apps.mkdir(parents=True, exist_ok=True)
    version = match[0]
    destination = apps / f"{name}-{version}"
    if name == "meshlab":
        destination = apps / f"{name}-{version}.AppImage"
        shutil.copy2(archive_path, destination)
        destination.chmod(0o755)
        executable = destination
    else:
        if not destination.exists():
            with tempfile.TemporaryDirectory(prefix=f".{name}-", dir=apps) as tmp:
                unpacked = Path(tmp) / "package"
                unpacked.mkdir()
                with tarfile.open(archive_path) as archive:
                    # Python 3.12 的 data filter 拒绝越界路径、设备节点和不安全链接。
                    archive.extractall(unpacked, filter="data")
                children = list(unpacked.iterdir())
                if len(children) != 1 or not children[0].is_dir():
                    raise ValueError("压缩包不符合单顶层目录布局")
                children[0].rename(destination)
        executable = destination / ("bin/node" if name == "nodejs" else name)
        if not executable.is_file():
            raise ValueError(f"找不到可执行文件：{executable}")
    bin_dir = local / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    commands = {"node": executable, "npm": destination / "bin/npm",
                "npx": destination / "bin/npx"} if name == "nodejs" else {name: executable}
    for command, program in commands.items():
        if not program.is_file():
            raise ValueError(f"找不到可执行文件：{program}")
        link = bin_dir / command
        if link.exists() and not link.is_symlink():
            raise ValueError(f"{link} 已存在且不是符号链接，请手动处理")
    for command, program in commands.items():
        link = bin_dir / command
        temp_link = bin_dir / f".{command}.tmp"
        temp_link.unlink(missing_ok=True)
        temp_link.symlink_to(program)
        temp_link.replace(link)
    if name == "nodejs":
        print(f"已安装 {name} {version}：{bin_dir}")
        return
    desktop_dir = local / "share/applications"
    desktop_dir.mkdir(parents=True, exist_ok=True)
    # Desktop Entry 的 Exec 有独立转义规则。
    escaped = str(executable).replace("\\", "\\\\").replace('"', '\\"').replace("`", "\\`").replace("$", "\\$").replace("%", "%%")
    desktop = (
        "[Desktop Entry]\nType=Application\n"
        f"Name={name.capitalize()}\nExec=\"{escaped}\" %f\n"
        "Terminal=false\nCategories=Education;Science;\n"
    )
    (desktop_dir / f"ubuntu-init-{name}.desktop").write_text(desktop)
    print(f"已安装 {name} {version}：{executable}")
    print(f"桌面菜单已添加入口；命令行入口：{link}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("app", choices=["blender", "zotero", "meshlab", "nodejs"])
    args = parser.parse_args()
    try:
        install(args.app)
    except (ValueError, OSError, KeyError, tarfile.TarError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"安装失败：{error}\n")
