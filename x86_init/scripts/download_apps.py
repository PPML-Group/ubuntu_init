#!/usr/bin/env python3
"""Resolve and cache Linux amd64 installers. Never execute downloaded files."""

import argparse
import datetime
import fcntl
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "Mozilla/5.0 (Ubuntu; Linux x86_64) ubuntu-init/1.0"


def fetch(url, binary=False):
    """Fetch small upstream metadata, respecting the user's proxy variables."""
    if not url.startswith("https://"):
        raise ValueError(f"下载来源必须使用 HTTPS：{url}")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                data = response.read()
            return data if binary else data.decode("utf-8")
        except OSError:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


def version_key(value):
    return tuple(map(int, re.findall(r"\d+", value)))


def artifact(url, version, **extra):
    name = urllib.parse.unquote(Path(urllib.parse.urlparse(url).path).name)
    if not name or name in (".", "..") or "/" in name or "\\" in name:
        raise ValueError(f"无效的下载文件名：{name}")
    if not url.startswith("https://"):
        raise ValueError("下载来源必须使用 HTTPS")
    return dict(url=url, version=version, filename=name, **extra)


def resolve(app):
    # 将 resolver 改成 static，并设置 url/version/sha256，可固定任意版本。
    kind = app["resolver"]
    if kind == "static":
        return artifact(app["url"], app["version"], sha256=app.get("sha256"))
    if kind == "github":
        release = app.get("tag")
        endpoint = "tags/" + urllib.parse.quote(release, safe="") if release else "latest"
        data = json.loads(fetch(f"https://api.github.com/repos/{app['repo']}/releases/{endpoint}"))
        if data.get("draft") or (data.get("prerelease") and not release):
            raise ValueError("上游返回了非正式版本")
        assets = [a for a in data["assets"] if re.search(app["asset_pattern"], a["name"])]
        if len(assets) != 1:
            raise ValueError(f"预期一个 amd64 安装包，实际匹配 {len(assets)} 个")
        asset = assets[0]
        digest = asset.get("digest") or ""
        return artifact(asset["browser_download_url"], data["tag_name"],
                        size=asset["size"],
                        sha256=digest.removeprefix("sha256:") if digest.startswith("sha256:") else None)
    if kind == "vscode":
        data = json.loads(fetch("https://update.code.visualstudio.com/api/update/linux-deb-x64/stable/latest"))
        return artifact(data["url"], data["productVersion"], sha256=data["sha256hash"])
    if kind == "nodejs":
        releases = json.loads(fetch("https://nodejs.org/dist/index.json"))
        release = max((r for r in releases if r.get("lts") and "linux-x64" in r["files"]),
                      key=lambda r: version_key(r["version"]))
        version = release["version"]
        base = f"https://nodejs.org/dist/{version}/"
        name = f"node-{version}-linux-x64.tar.xz"
        checksums = fetch(base + "SHASUMS256.txt")
        digest = next(line.split()[0] for line in checksums.splitlines()
                      if line.split()[-1] == name)
        return artifact(base + name, version, sha256=digest)
    if kind == "miniconda":
        base = "https://repo.anaconda.com/miniconda/"
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", fetch(base), re.S)
        candidates = []
        for row in rows:
            name = re.search(rf'Miniconda3-py{app["python"]}_[\d.-]+-Linux-x86_64\.sh', row)
            digest = re.search(r"\b[0-9a-f]{64}\b", row)
            if name and digest:
                candidates.append((name[0], digest[0]))
        name, digest = max(candidates, key=lambda pair: version_key(pair[0]))
        return artifact(base + name, name.removeprefix("Miniconda3-").removesuffix("-Linux-x86_64.sh"),
                        sha256=digest)
    if kind == "blender":
        if app.get("series"):
            base = f"https://download.blender.org/release/Blender{app['series']}/"
            index = fetch(base + "?C=M;O=D")
            versions = re.findall(r"blender-(" + re.escape(app["series"]) + r"\.\d+)-linux-x64\.tar\.xz", index)
        else:
            # 官方下载首页只推荐当前稳定版；不从归档目录猜测开发版/预发布版。
            page = fetch("https://www.blender.org/download/")
            versions = re.findall(
                r'https://www\.blender\.org/download/release/Blender\d+\.\d+/'
                r'blender-(\d+\.\d+\.\d+)-linux-x64\.tar\.xz/', page)
        if not versions:
            raise ValueError("Blender 官方页面未返回 Linux x64 稳定版")
        version = max(versions, key=version_key)
        base = f"https://download.blender.org/release/Blender{version.rsplit('.', 1)[0]}/"
        name = f"blender-{version}-linux-x64.tar.xz"
        checksums = fetch(base + f"blender-{version}.sha256")
        digest = next(line.split()[0] for line in checksums.splitlines()
                      if line.split()[-1].lstrip("*") == name)
        return artifact(base + name, version, sha256=digest)
    if kind == "sogou":
        page = fetch(app["homepage"]).replace(r"\u002F", "/").replace(r"\/", "/")
        urls = re.findall(
            r"https://ime-sec\.gtimg\.com/pc/dl/[^\"\\<>\s]*"
            r"sogoupinyin_[\d.]+_amd64\.deb", page)
        if not urls:
            raise ValueError("搜狗官网未返回 Linux amd64 DEB")
        url = max(set(urls), key=lambda value: version_key(
            re.search(r"sogoupinyin_([\d.]+)_", value)[1]))
        return artifact(url, re.search(r"sogoupinyin_([\d.]+)_", url)[1])
    if kind == "todesk":
        page = fetch(app["homepage"]).replace(r"\u002F", "/")
        # 官网 Nuxt 数据同时包含灰度版本，不能简单选择页面上的最高版本。
        page = re.sub(r'\w*gray_link:"[^"]*"', "", page)
        urls = re.findall(r"https://dl\.todesk\.com/linux/todesk-v[\d.]+-amd64\.deb", page)
        url = max(urls, key=version_key)
        return artifact(url, re.search(r"todesk-v([\d.]+)-", url)[1],
                        referer=app["homepage"])
    if kind == "sunlogin":
        # 官方下载页使用的个人版接口；downloadurl 本身可能是 RPM。
        data = json.loads(fetch("https://client-webapi.oray.com/softwares/SUNLOGIN_X_LINUX?x64=1&versiontype=stable"))
        urls = [a["url"] for a in data["downloadurlmultiple"] if a["url"].endswith("_amd64.deb")]
        if len(urls) != 1:
            raise ValueError("向日葵接口未返回唯一的 amd64 DEB")
        return artifact(urls[0], data["versionno"])
    if kind == "zotero":
        request = urllib.request.Request(
            "https://www.zotero.org/download/client/dl?channel=release&platform=linux-x86_64",
            method="HEAD", headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(request, timeout=30) as response:
            url = response.url
        match = re.search(r"Zotero-([\d.]+)_linux-x86_64", url)
        if not match:
            raise ValueError("无法从 Zotero 官方重定向识别版本")
        return artifact(url, match[1])
    raise ValueError(f"未知来源类型：{kind}")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate(path, info, fmt):
    if path.stat().st_size < 4096:
        raise ValueError("文件过小，可能是网站验证/错误页面；可用浏览器下载原文件到对应类型目录后重试")
    if info.get("size") and path.stat().st_size != info["size"]:
        raise ValueError("文件大小与发布信息不符")
    digest = sha256(path)
    if info.get("sha256") and digest.lower() != info["sha256"].lower():
        raise ValueError("SHA256 校验失败")
    if fmt == "deb":
        result = subprocess.run(
            ["dpkg-deb", "--field", str(path), "Architecture"], check=True, capture_output=True, text=True)
        if result.stdout.strip() not in ("amd64", "all"):
            raise ValueError("DEB 不是 amd64/all 架构")
        subprocess.run(["dpkg-deb", "--contents", str(path)],
                       stdout=subprocess.DEVNULL, check=True)
    elif fmt == "tar":
        with tarfile.open(path) as archive:
            # 确认包含文件；下面的 tar -tf 再完整检查压缩流，不解压、不执行。
            if not any(member.isfile() for member in archive):
                raise ValueError("压缩包没有文件")
        subprocess.run(["tar", "-tf", str(path)], stdout=subprocess.DEVNULL, check=True)
    else:
        with path.open("rb") as file:
            magic = file.read(256)
        if fmt == "sh" and not magic.startswith(b"#!"):
            raise ValueError("不是 Shell 安装器")
        if fmt == "appimage" and (magic[:4] != b"\x7fELF" or magic[8:11] not in (b"AI\x01", b"AI\x02")):
            raise ValueError("不是 AppImage")
    return digest


def save_json(path, data):
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    temp.replace(path)


def load_json(path):
    return json.loads(path.read_text()) if path.exists() else {}


def local_path(output, relative):
    target = (output / relative).resolve()
    if not target.is_relative_to(output.resolve()):
        raise ValueError("缓存路径超出下载目录")
    return target


def download(output, info, fmt, refresh=False):
    folder = {"deb": "deb", "sh": "installers", "tar": "archives", "appimage": "archives"}[fmt]
    relative = str(Path(folder) / info["filename"])
    target = local_path(output, relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not refresh:
        try:
            digest = validate(target, info, fmt)
            print(f"  已验证，跳过：{relative}", flush=True)
            return relative, digest
        except (ValueError, OSError, subprocess.CalledProcessError, tarfile.TarError):
            print(f"  现有文件校验失败，重新下载：{relative}", flush=True)
    partial = target.with_name(target.name + ".part")
    command = ["curl", "--fail", "--location", "--proto", "=https", "--proto-redir", "=https",
               "--retry", "3", "--connect-timeout", "20", "--speed-time", "60",
               "--speed-limit", "1024", "--silent", "--show-error",
               "--user-agent", USER_AGENT, "--output", str(partial)]
    if info.get("referer"):
        command += ["--referer", info["referer"]]
    url = info["url"]
    parsed = urllib.parse.urlparse(url)
    if parsed.hostname == "ime-sec.gtimg.com" and parsed.path.startswith("/pc/dl/"):
        # 与搜狗官网下载按钮的公开前端逻辑一致（72343 模块）。
        # 缓存保留不带时间的来源地址，每次实际传输时生成新地址，避免过期。
        # 此 MD5 仅是官网 URL 参数，不用于验证安装包完整性。
        stamp = datetime.datetime.now(
            datetime.timezone(datetime.timedelta(hours=8))).strftime("%Y%m%d%H%M")
        token = hashlib.md5(
            ("44tv2uj7ct7j0gfixf19cs6bdvqdhi" + stamp + parsed.path).encode()).hexdigest()
        url = f"https://ime-sec.gtimg.com/{stamp}/{token}{parsed.path}"
    if parsed.hostname == "dl.todesk.com":
        # 此 CDN 对 curl 返回验证页，但标准库 HTTPS 请求能取得公开安装包。
        # 每次重试完整传输；成功后仍执行相同的 DEB 格式和完整性检查。
        request = urllib.request.Request(url, headers={
            "User-Agent": USER_AGENT, "Referer": info.get("referer", "https://www.todesk.com/")})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    if not response.url.startswith("https://"):
                        raise ValueError("下载重定向必须使用 HTTPS")
                    with partial.open("wb") as file:
                        shutil.copyfileobj(response, file, length=1024 * 1024)
                break
            except OSError:
                if attempt == 2:
                    raise
                time.sleep(attempt + 1)
    else:
        result = subprocess.run(command + ["--continue-at", "-", url])
        if result.returncode == 33:  # 源站不支持 Range 时重新开始。
            partial.unlink(missing_ok=True)
            result = subprocess.run(command + [url])
        result.check_returncode()
    try:
        digest = validate(partial, info, fmt)
    except Exception:
        partial.unlink(missing_ok=True)
        raise
    partial.replace(target)
    return relative, digest


def run(args, apps):
    selected = args.apps or [name for name, app in apps.items() if app["group"] == (args.group or "default")]
    unknown = set(selected) - apps.keys()
    if unknown:
        raise ValueError("未知软件：" + ", ".join(sorted(unknown)))
    output = args.output.resolve()
    manifest_path = output / "manifest.json"
    manifest = load_json(manifest_path)
    failed = []
    for name in dict.fromkeys(selected):
        app = apps[name]
        print(f"[{name}] {app['label']}", flush=True)
        try:
            previous = manifest.get(name)
            if args.verify:
                if not previous:
                    raise ValueError("尚未下载")
                validate(local_path(output, previous["path"]), previous, app["format"])
                print(f"  校验通过：{previous['path']}")
                continue
            # 已验证文件可直接复用，不必每次访问网络；清单改变或 --update 时重新解析。
            if not args.update and previous and previous.get("source") == app:
                target = local_path(output, previous["path"])
                if target.exists():
                    try:
                        validate(target, previous, app["format"])
                        print(f"  已验证，跳过：{previous['path']}", flush=True)
                        continue
                    except (ValueError, OSError, subprocess.CalledProcessError, tarfile.TarError):
                        pass
            info = resolve(app)
            print(f"  {info['version']}  {info['url']}", flush=True)
            if args.dry_run:
                continue
            download_info = dict(info)
            refresh = bool(args.update and app.get("mutable"))
            if (not refresh and previous and previous["url"] == info["url"]
                    and previous["version"] == info["version"] and not info.get("sha256")):
                # 无上游摘要时仍检查本机已记录的同一版本摘要，不能接纳损坏后的缓存。
                download_info["sha256"] = previous["sha256"]
            relative, digest = download(output, download_info, app["format"], refresh=refresh)
            manifest[name] = dict(
                info, path=relative, sha256=digest, source=app,
                upstream_sha256=info.get("sha256"), format=app["format"],
                size=local_path(output, relative).stat().st_size,
                downloaded_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
            if app["format"] == "deb":
                manifest[name]["package_version"] = subprocess.check_output(
                    ["dpkg-deb", "--field", str(local_path(output, relative)), "Version"],
                    text=True).strip()
            save_json(manifest_path, manifest)
            print(f"  完成：{relative}", flush=True)
        except (ValueError, KeyError, OSError, subprocess.CalledProcessError,
                tarfile.TarError, StopIteration) as error:
            failed.append(name)
            print(f"  失败：{error}", file=sys.stderr, flush=True)
    if failed:
        print("未完成：" + ", ".join(failed) + "；修复网络或来源后重新运行即可。", file=sys.stderr)
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apps", nargs="*", help="软件 ID；默认下载 default 组")
    parser.add_argument("--group", choices=["default", "research", "daily"])
    parser.add_argument("--list", action="store_true", help="仅列出软件，不联网")
    parser.add_argument("--dry-run", action="store_true", help="解析来源但不下载、不写缓存")
    parser.add_argument("--update", action="store_true", help="重新解析上游版本")
    parser.add_argument("--verify", action="store_true", help="离线验证已下载文件")
    parser.add_argument("--config", type=Path, default=ROOT / "config/apps.json")
    parser.add_argument("--output", type=Path, default=ROOT,
                        help="下载根目录；其下分为deb、archives、installers，默认x86_init")
    args = parser.parse_args()
    if args.apps and args.group:
        parser.error("软件 ID 与 --group 请选择一种")
    if args.verify and (args.dry_run or args.update):
        parser.error("--verify 不能与 --dry-run/--update 同用")
    apps = load_json(args.config)
    if not apps:
        parser.error("软件清单为空或不存在")
    if args.list:
        for name, app in apps.items():
            print(f"{name:18} {app['group']:10} {app['label']}")
        return 0
    for tool in ("curl", "dpkg-deb", "tar"):
        if not shutil.which(tool):
            parser.error(f"缺少 {tool}，请先安装 curl dpkg tar xz-utils bzip2")
    if args.dry_run:
        return run(args, apps)
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / ".download.lock").open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            parser.error("此目录已有下载任务，请等其完成")
        return run(args, apps)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError) as error:
        print(f"错误：{error}", file=sys.stderr)
        sys.exit(1)
