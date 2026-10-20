"""Check USB installation with local files, without a download manifest or real apt."""
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "x86_init/scripts"))
import install_archive


class LocalInstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "U盘 copy" / "x86_init"
        (self.root / "sh").mkdir(parents=True)
        (self.root / "deb").mkdir()
        (self.root / "archives").mkdir()
        shutil.copy2(REPO / "x86_init/sh/deb_install.sh", self.root / "sh")
        self.log = Path(self.tmp.name) / "commands.jsonl"
        tools = Path(self.tmp.name) / "tools"
        tools.mkdir()
        sudo = tools / "sudo"
        sudo.write_text(
            "#!/usr/bin/python3\nimport json, os, sys\n"
            "with open(os.environ['INSTALL_TEST_LOG'], 'a') as f:\n"
            "    f.write(json.dumps(sys.argv[1:]) + '\\n')\n"
            "sys.exit(int(os.environ.get('INSTALL_TEST_EXIT', '0')))\n"
        )
        sudo.chmod(0o755)
        self.env = dict(os.environ, PATH=f"{tools}:{os.environ['PATH']}",
                        INSTALL_TEST_LOG=str(self.log))

    def run_debs(self, *args):
        return subprocess.run(
            ["bash", str(self.root / "sh/deb_install.sh"), *args],
            cwd=self.tmp.name, env=self.env, capture_output=True, text=True)

    def test_usb_directory_without_manifest_and_with_spaces(self):
        package = self.root / "deb/hand downloaded app.deb"
        package.touch()
        (self.root / "deb/incomplete.deb.part").touch()
        nested = self.root / "deb/subfolder"
        nested.mkdir()
        (nested / "not-selected.deb").touch()
        result = self.run_debs()
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = [json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertEqual(calls[0], ["apt", "update"])
        self.assertEqual(calls[1][:2], ["apt", "install"])
        self.assertEqual(Path(calls[1][2]).resolve(), package)
        self.assertEqual(calls[1][3:], ["-y"])

    def test_empty_directory_does_not_call_apt(self):
        self.assertEqual(self.run_debs().returncode, 0)
        self.assertFalse(self.log.exists())

    def test_apt_failure_stops_install(self):
        (self.root / "deb/app.deb").touch()
        self.env["INSTALL_TEST_EXIT"] = "100"
        result = self.run_debs()
        self.assertEqual(result.returncode, 100)
        self.assertEqual(len(self.log.read_text().splitlines()), 1)
        self.assertNotIn("已安装", result.stdout)

    def test_archive_installs_without_manifest_or_downloader(self):
        archive = self.root / "archives/blender-5.2.2-linux-x64.tar.xz"
        payload = b"local fixture, never executed"
        with tarfile.open(archive, "w:xz") as output:
            member = tarfile.TarInfo("blender-5.2.2-linux-x64/blender")
            member.size = len(payload)
            member.mode = 0o755
            output.addfile(member, io.BytesIO(payload))
        home = Path(self.tmp.name) / "target home"
        with patch.object(install_archive, "ROOT", self.root), \
                patch.object(install_archive.os, "geteuid", return_value=1000), \
                patch.object(install_archive.Path, "home", return_value=home), \
                contextlib.redirect_stdout(io.StringIO()):
            install_archive.install("blender")
        self.assertEqual((home / ".local/bin/blender").read_bytes(), payload)
        self.assertTrue((home / ".local/share/applications/ubuntu-init-blender.desktop").exists())
        self.assertFalse((self.root / "manifest.json").exists())

    def test_init_runs_original_sequence_from_another_directory(self):
        shutil.copy2(REPO / "x86_init/init.sh", self.root)
        expected = ["apt_install", "deb_install", "sogou", "fishros_ros", "zsh",
                    "miniconda", "blender", "fix_time", "codex"]
        for name in expected:
            (self.root / f"sh/{name}.sh").write_text(
                f'#!/bin/bash\nprintf "%s\\n" "{name}" >> "$INSTALL_TEST_LOG"\n')
        result = subprocess.run(["bash", str(self.root / "init.sh")],
                                cwd=self.tmp.name, env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.log.read_text().splitlines(), expected)

    def test_codex_uses_existing_npm_and_stops_on_install_failure(self):
        shutil.copy2(REPO / "x86_init/sh/codex.sh", self.root / "sh")
        # 即使U盘带着旧副本，Codex安装也不再自动迁移skills。
        (self.root / "skills").mkdir()
        tools = Path(self.env["PATH"].split(":")[0])
        real_node = shutil.which("node")
        self.assertIsNotNone(real_node)
        (tools / "node").write_text(
            "#!/usr/bin/python3\nimport json, os, subprocess, sys\n"
            "setup = \"Object.defineProperty(process.versions, 'node', {value: \" + "
            "json.dumps(os.environ.get('INSTALL_TEST_NODE_VERSION', '22.20.0')) + \"});\\n\"\n"
            f"sys.exit(subprocess.call([{real_node!r}, '-e', setup + sys.argv[2]]))\n")
        (tools / "node").chmod(0o755)
        prefix = self.root / "node-prefix"
        (prefix / "bin").mkdir(parents=True)
        (prefix / "bin/codex").write_text("#!/bin/bash\necho codex-fixture\n")
        (prefix / "bin/codex").chmod(0o755)
        (tools / "npm").write_text(
            "#!/usr/bin/python3\nimport json, os, sys\n"
            "if sys.argv[1:] == ['--version']:\n"
            "    print('10.0.0'); sys.exit(0)\n"
            "with open(os.environ['INSTALL_TEST_LOG'], 'a') as f:\n"
            "    f.write(json.dumps(sys.argv[1:]) + '\\n')\n"
            "if sys.argv[1:] == ['prefix', '-g']:\n"
            "    print(os.environ['INSTALL_TEST_PREFIX'])\n"
            "elif sys.argv[1:] == ['install', '-g', '@openai/codex@latest']:\n"
            "    sys.exit(int(os.environ['INSTALL_TEST_NPM_EXIT']))\n"
            "else:\n"
            "    sys.exit(99)\n"
        )
        (tools / "npm").chmod(0o755)
        for code in [0, 42]:
            with self.subTest(npm_exit=code):
                self.log.unlink(missing_ok=True)
                env = dict(self.env, INSTALL_TEST_PREFIX=str(prefix),
                           INSTALL_TEST_NPM_EXIT=str(code))
                result = subprocess.run(["bash", str(self.root / "sh/codex.sh")],
                                        env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, code, result.stderr)
                calls = [json.loads(line) for line in self.log.read_text().splitlines()]
                self.assertEqual(calls, [["prefix", "-g"],
                                        ["install", "-g", "@openai/codex@latest"]])
                self.assertEqual("codex-fixture" in result.stdout, code == 0)
                self.assertEqual("Codex已安装" in result.stdout, code == 0)
                self.assertEqual("Skills按README末尾清单安装和更新" in result.stdout, code == 0)

        # 旧Node必须转用本地包，安装后不能继续命中Bash缓存的旧命令路径。
        home = self.root / "home"
        home.mkdir()
        scripts = self.root / "scripts"
        scripts.mkdir()
        (scripts / "install_archive.py").write_text(
            "from pathlib import Path\nimport shutil, sys\n"
            "assert sys.argv[1:] == ['nodejs']\n"
            "target = Path.home() / '.local/bin'\n"
            "target.mkdir(parents=True)\n"
            "(target / 'node').write_text('#!/bin/bash\\nexit 0\\n')\n"
            "(target / 'node').chmod(0o755)\n"
            f"shutil.copy2({str(tools / 'npm')!r}, target / 'npm')\n")
        self.log.unlink(missing_ok=True)
        result = subprocess.run(
            ["bash", str(self.root / "sh/codex.sh")],
            env=dict(self.env, HOME=str(home), NVM_DIR=str(home / ".nvm"),
                     INSTALL_TEST_PREFIX=str(prefix), INSTALL_TEST_NPM_EXIT="0",
                     INSTALL_TEST_NODE_VERSION="22.19.0"),
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((home / ".local/bin/node").is_file())
        self.assertIn("Codex已安装", result.stdout)

    def test_node_preserves_relative_npm_links(self):
        archive = self.root / "archives/node-v24.22.0-linux-x64.tar.xz"
        prefix = "node-v24.22.0-linux-x64"
        with tarfile.open(archive, "w:xz") as output:
            for name in ["bin/node", "lib/node_modules/npm/bin/npm-cli.js",
                         "lib/node_modules/npm/bin/npx-cli.js"]:
                member = tarfile.TarInfo(f"{prefix}/{name}")
                member.size, member.mode = 4, 0o755
                output.addfile(member, io.BytesIO(b"test"))
            for name in ["npm", "npx"]:
                member = tarfile.TarInfo(f"{prefix}/bin/{name}")
                member.type = tarfile.SYMTYPE
                member.linkname = f"../lib/node_modules/npm/bin/{name}-cli.js"
                output.addfile(member)
        home = self.root / "home"
        with patch.object(install_archive, "ROOT", self.root), \
                patch.object(install_archive.os, "geteuid", return_value=1000), \
                patch.object(install_archive.Path, "home", return_value=home), \
                contextlib.redirect_stdout(io.StringIO()):
            install_archive.install("nodejs")
        for name in ["node", "npm", "npx"]:
            self.assertEqual((home / ".local/bin" / name).read_bytes(), b"test")

    def test_zsh_local_install_preserves_conda_and_is_repeatable(self):
        shutil.copy2(REPO / "x86_init/sh/zsh.sh", self.root / "sh")
        for name, marker, function in [
                ("oh-my-zsh", "oh-my-zsh.sh", "omz"),
                ("zsh-autosuggestions", "zsh-autosuggestions.zsh", "_zsh_autosuggest_start"),
                ("zsh-syntax-highlighting", "zsh-syntax-highlighting.zsh", "_zsh_highlight")]:
            folder = self.root / "github" / name
            folder.mkdir(parents=True)
            (folder / marker).write_text(f"function {function} {{ :; }}\n")
        with (self.root / "github/oh-my-zsh/oh-my-zsh.sh").open("a") as stream:
            stream.write('autoload -Uz compinit\ncompinit -d "$HOME/.zcompdump"\n')
        completion = self.root / "github/conda-zsh-completion"
        completion.mkdir()
        (completion / "_conda").write_text("#compdef conda\nreturn 0\n")
        home = self.root / "home"
        home.mkdir()
        user_config = ("export KEEP_ME=yes\nZSH_CACHE_DIR=/tmp/unused-zsh-cache\n"
                       "plugins=(git custom)\n"
                       "# >>> conda initialize >>>\n# kept\n# <<< conda initialize <<<\n")
        fishros = ("# >>> fishros initialize >>>\nsource /opt/ros/jazzy/setup.zsh\n"
                   "# <<< fishros initialize <<<\n")
        original = user_config + fishros
        (home / ".zshrc").write_text(original)
        (home / ".nvm").mkdir()
        (home / ".nvm/nvm.sh").write_text("function nvm { :; }\n")
        tools = Path(self.env["PATH"].split(":")[0])
        (tools / "git").write_text("#!/bin/bash\nexit 99\n")
        (tools / "git").chmod(0o755)
        (tools / "register-python-argcomplete").write_text(
            "#!/bin/bash\n[[ $* == '--shell zsh ros2 colcon' ]] || exit 33\n"
            "echo 'compdef _python_argcomplete ros2 colcon'\n")
        (tools / "register-python-argcomplete").chmod(0o755)
        env = dict(self.env, HOME=str(home), NVM_DIR=str(home / ".nvm"))
        env.pop("ZSH", None)
        env.pop("ZSH_CUSTOM", None)
        env.pop("ZDOTDIR", None)
        command = ["bash", str(self.root / "sh/zsh.sh")]
        for index in range(2):
            if index:
                # 鱼香重跑时移除旧段，再追加到文件末尾。
                rc = home / ".zshrc"
                rc.write_text(rc.read_text().replace(fishros, "") + fishros)
            result = subprocess.run(command, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        text = (home / ".zshrc").read_text()
        self.assertIn(user_config, text)
        self.assertEqual(text.count("# >>> ubuntu-init zsh >>>"), 1)
        self.assertIn(fishros, text)
        self.assertLess(text.index(fishros), text.index("# >>> ubuntu-init zsh >>>"))
        self.assertEqual(text.count("source /opt/ros/jazzy/setup.zsh"), 1)
        self.assertNotIn('source "/opt/ros/jazzy/setup.zsh"', text)
        self.assertNotIn("/humble", text)
        self.assertEqual((home / ".zshrc.ubuntu-init.bak").read_text(), original)
        subprocess.run(["zsh", "-n", str(home / ".zshrc")], check=True)
        # 该测试机未安装Jazzy，仅替换临时HOME中的ROS入口。
        (home / ".zshrc").write_text(text.replace(
            "source /opt/ros/jazzy/setup.zsh", "export ROS_TEST=loaded"))
        result = subprocess.run(
            ["zsh", "-ic", 'print -r -- "$KEEP_ME|$+functions[omz]|$+functions[nvm]|${plugins[*]}|${_comps[conda]}|$ROS_TEST|$RMW_IMPLEMENTATION|${_comps[ros2]}|${_comps[colcon]}"'],
            env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertIn("yes|1|1|git custom|_conda|loaded|rmw_cyclonedds_cpp|_python_argcomplete|_python_argcomplete", result.stdout)

    def test_fishros_requests_zsh_even_when_parent_shell_is_bash(self):
        home = self.root / "home"
        home.mkdir()
        tools = Path(self.env["PATH"].split(":")[0])
        (tools / "wget").write_text(
            "#!/usr/bin/python3\nimport pathlib, sys\n"
            "pathlib.Path(sys.argv[sys.argv.index('-O') + 1]).write_text("
            "'[[ $SHELL == */zsh ]] || exit 31\\n"
            '[[ -f "$HOME/.zshrc" ]] || exit 32\\n'
            'printf "# >>> fishros initialize >>>\\\\nsource /opt/ros/jazzy/setup.zsh\\\\n# <<< fishros initialize <<<\\\\n" >> "$HOME/.zshrc"\\n'
            "')\n")
        # 模拟sudo的环境重置，再执行显式env；不提升权限。
        (tools / "sudo").write_text(
            "#!/usr/bin/python3\nimport json, os, subprocess, sys\n"
            "with open(os.environ['INSTALL_TEST_LOG'], 'a') as f:\n"
            "    f.write(json.dumps(sys.argv[1:]) + '\\n')\n"
            "if sys.argv[1] == 'env':\n"
            "    os.environ['SHELL'] = '/bin/bash'\n"
            "    sys.exit(subprocess.call(sys.argv[1:]))\n")
        (tools / "dpkg-query").write_text("#!/bin/bash\nprintf 'install ok installed'\n")
        for name in ("wget", "sudo", "dpkg-query"):
            (tools / name).chmod(0o755)
        result = subprocess.run(
            ["bash", str(REPO / "x86_init/sh/fishros_ros.sh")],
            env=dict(self.env, HOME=str(home), SHELL="/bin/bash"),
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("source /opt/ros/jazzy/setup.zsh", (home / ".zshrc").read_text())
        calls = [json.loads(line) for line in self.log.read_text().splitlines()]
        installed = calls[-1]
        self.assertIn("ros-jazzy-rmw-cyclonedds-cpp", installed)
        self.assertIn("ros-jazzy-desktop-full", installed)
        self.assertFalse(any("ros-gz" in item or "gz-ros2" in item for item in installed))

    def test_existing_miniconda_is_initialized_for_both_shells(self):
        home = self.root / "home"
        binary = home / "miniconda3/bin/conda"
        binary.parent.mkdir(parents=True)
        binary.write_text(
            "#!/usr/bin/python3\nimport json, os, sys\n"
            "with open(os.environ['INSTALL_TEST_LOG'], 'a') as f:\n"
            "    f.write(json.dumps(sys.argv[1:]) + '\\n')\n")
        binary.chmod(0o755)
        result = subprocess.run(["bash", str(REPO / "x86_init/sh/miniconda.sh")],
                                env=dict(self.env, HOME=str(home)),
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = [json.loads(line) for line in self.log.read_text().splitlines()]
        self.assertEqual(calls, [["init", "bash", "zsh"],
                                 ["config", "--set", "auto_activate_base", "false"]])

    def test_time_fix_requires_synchronized_clock(self):
        tools = Path(self.env["PATH"].split(":")[0])
        timedatectl = tools / "timedatectl"
        timedatectl.write_text(
            "#!/usr/bin/python3\nimport os, sys\nfrom pathlib import Path\n"
            "if sys.argv[1:2] == ['show']:\n"
            "    countfile = Path(os.environ['INSTALL_TEST_LOG'] + '.polls')\n"
            "    count = int(countfile.read_text()) + 1 if countfile.exists() else 1\n"
            "    countfile.write_text(str(count))\n"
            "    state = os.environ['INSTALL_TEST_SYNC']\n"
            "    print(('yes' if count >= 3 else 'no') if state == 'delayed' else state)\n")
        timedatectl.chmod(0o755)
        (tools / "sleep").write_text("#!/bin/bash\nexit 0\n")
        (tools / "sleep").chmod(0o755)
        for synced in ["no", "yes", "delayed"]:
            with self.subTest(synced=synced):
                self.log.unlink(missing_ok=True)
                Path(str(self.log) + ".polls").unlink(missing_ok=True)
                result = subprocess.run(
                    ["bash", str(REPO / "x86_init/sh/fix_time.sh")],
                    env=dict(self.env, INSTALL_TEST_SYNC=synced), capture_output=True, text=True)
                calls = [json.loads(line) for line in self.log.read_text().splitlines()]
                self.assertEqual(calls[0], ["timedatectl", "set-ntp", "true"])
                if synced == "no":
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(len(calls), 1)
                else:
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(calls[1], ["timedatectl", "set-local-rtc", "1"])


if __name__ == "__main__":
    unittest.main()
