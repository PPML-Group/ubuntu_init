import argparse
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "x86_init/scripts"))
import download_apps as downloader


class DownloadTests(unittest.TestCase):
    def test_node_selects_lts_with_official_checksum(self):
        releases = [
            {"version": "v26.0.0", "lts": False, "files": ["linux-x64"]},
            {"version": "v24.10.0", "lts": "Krypton", "files": ["linux-x64"]},
            {"version": "v24.9.0", "lts": "Krypton", "files": ["linux-x64"]},
        ]
        digest = "a" * 64
        with patch.object(downloader, "fetch", side_effect=[
            json.dumps(releases), f"{digest}  node-v24.10.0-linux-x64.tar.xz\n"
        ]):
            info = downloader.resolve({"resolver": "nodejs"})
        self.assertEqual(info["version"], "v24.10.0")
        self.assertEqual(info["sha256"], digest)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.output = Path(self.tmp.name)
        self.payload = b"#!/bin/bash\n# fixture, never executed\n" + b"#" * 5000
        self.app = {
            "label": "fixture", "group": "default", "resolver": "static",
            "url": "https://example.test/installer.sh", "version": "1", "format": "sh",
        }
        self.args = argparse.Namespace(
            apps=[], group=None, output=self.output,
            update=False, verify=False, dry_run=False)

    def curl(self, command, **kwargs):
        self.assertEqual(command[0], "curl")
        Path(command[command.index("--output") + 1]).write_bytes(self.payload)
        return subprocess.CompletedProcess(command, 0)

    def run_download(self, apps=None):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return downloader.run(self.args, apps or {"fixture": self.app})

    def test_download_and_offline_reuse(self):
        with patch.object(downloader.subprocess, "run", side_effect=self.curl) as curl:
            self.assertEqual(self.run_download(), 0)
            self.assertEqual(curl.call_count, 1)
        with patch.object(downloader, "resolve", side_effect=AssertionError("network")):
            self.assertEqual(self.run_download(), 0)
            self.args.verify = True
            self.assertEqual(self.run_download(), 0)
        record = json.loads((self.output / "manifest.json").read_text())["fixture"]
        self.assertEqual(record["sha256"], downloader.sha256(self.output / record["path"]))
        self.assertIsNone(record["upstream_sha256"])

    def test_corruption_requires_redownload_even_without_upstream_checksum(self):
        with patch.object(downloader.subprocess, "run", side_effect=self.curl):
            self.assertEqual(self.run_download(), 0)
        cached = self.output / "installers/installer.sh"
        cached.write_bytes(self.payload[:-1] + b"X")
        with patch.object(downloader.subprocess, "run", side_effect=self.curl) as curl:
            self.assertEqual(self.run_download(), 0)
            self.assertEqual(curl.call_count, 1)
        self.assertEqual(cached.read_bytes(), self.payload)

    def test_failed_item_does_not_hide_success_or_write_manifest_entry(self):
        apps = {"bad": dict(self.app, resolver="invalid"), "good": self.app}
        with patch.object(downloader.subprocess, "run", side_effect=self.curl):
            self.assertEqual(self.run_download(apps), 1)
        self.assertEqual(set(json.loads((self.output / "manifest.json").read_text())), {"good"})

    def test_update_refreshes_mutable_url(self):
        self.app["mutable"] = True
        with patch.object(downloader.subprocess, "run", side_effect=self.curl):
            self.assertEqual(self.run_download(), 0)
        self.payload += b"# new release"
        self.args.update = True
        with patch.object(downloader.subprocess, "run", side_effect=self.curl) as curl:
            self.assertEqual(self.run_download(), 0)
            self.assertEqual(curl.call_count, 1)
        self.assertEqual((self.output / "installers/installer.sh").read_bytes(), self.payload)

    def test_html_is_not_cached_as_an_installer(self):
        self.payload = b"<html>" + b"x" * 5000 + b"</html>"
        with patch.object(downloader.subprocess, "run", side_effect=self.curl):
            self.assertEqual(self.run_download(), 1)
        self.assertFalse((self.output / "manifest.json").exists())
        self.assertFalse(list(self.output.rglob("*.part")))

    def test_checksum_mismatch_is_rejected(self):
        self.app["sha256"] = "0" * 64
        with patch.object(downloader.subprocess, "run", side_effect=self.curl):
            self.assertEqual(self.run_download(), 1)
        self.assertFalse((self.output / "manifest.json").exists())

    def test_unknown_app_fails_before_download(self):
        self.args.apps = ["typo"]
        with self.assertRaisesRegex(ValueError, "未知软件"):
            self.run_download()
        self.assertEqual(list(self.output.iterdir()), [])

    def test_dry_run_does_not_write_cache(self):
        self.args.dry_run = True
        self.assertEqual(self.run_download(), 0)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_path_traversal_is_rejected(self):
        with self.assertRaises(ValueError):
            downloader.local_path(self.output, "../outside")
        with self.assertRaises(ValueError):
            downloader.artifact("https://example.test/%2Ftmp%2Fbad.deb", "1")

    def test_resume_restarts_when_server_rejects_range(self):
        partial = self.output / "installers/installer.sh.part"
        partial.parent.mkdir()
        partial.write_bytes(self.payload[:100])
        calls = []

        def transfer(command, **kwargs):
            calls.append(command)
            if "--continue-at" in command:
                return subprocess.CompletedProcess(command, 33)
            return self.curl(command)

        with patch.object(downloader.subprocess, "run", side_effect=transfer):
            self.assertEqual(self.run_download(), 0)
        self.assertEqual(len(calls), 2)
        self.assertNotIn("--continue-at", calls[1])

    def test_failed_download_resolves_fresh_url_and_resumes_partial(self):
        partial = self.output / "installers/installer.sh.part"
        first = downloader.artifact(self.app["url"] + "?token=old", "1")
        second = downloader.artifact(self.app["url"] + "?token=new", "1")

        def interrupted(command, **kwargs):
            partial.write_bytes(self.payload[:100])
            return subprocess.CompletedProcess(command, 18)

        def resumed(command, **kwargs):
            self.assertEqual(command[-1], second["url"])
            self.assertIn("--continue-at", command)
            self.assertEqual(partial.read_bytes(), self.payload[:100])
            return self.curl(command)

        with patch.object(downloader, "resolve", side_effect=[first, second]) as resolve:
            with patch.object(downloader.subprocess, "run", side_effect=interrupted):
                self.assertEqual(self.run_download(), 1)
            self.assertEqual(list(self.output.rglob("*.json")), [])
            with patch.object(downloader.subprocess, "run", side_effect=resumed):
                self.assertEqual(self.run_download(), 0)
            self.assertEqual(resolve.call_count, 2)
        self.assertEqual([p.name for p in self.output.rglob("*.json")], ["manifest.json"])
        self.assertFalse(partial.exists())

    def test_todesk_excludes_gray_release(self):
        page = (
            'linux_deb_link_x64_new_gray_link:"https:\\u002F\\u002Fdl.todesk.com\\u002Flinux\\u002Ftodesk-v9.0.0.0-amd64.deb",'
            '"https:\\u002F\\u002Fdl.todesk.com\\u002Flinux\\u002Ftodesk-v4.9.7.0-amd64.deb"'
        )
        with patch.object(downloader, "fetch", return_value=page):
            result = downloader.resolve({"resolver": "todesk", "homepage": "https://example.test"})
        self.assertEqual(result["version"], "4.9.7.0")
        self.assertEqual(result["referer"], "https://example.test")

    def test_todesk_transport_retries_and_registers_only_valid_content(self):
        self.app["url"] = "https://dl.todesk.com/linux/fixture.sh"
        self.app["referer"] = "https://www.todesk.com/linux.html"
        response = io.BytesIO(self.payload)
        response.url = self.app["url"]
        with patch.object(downloader.urllib.request, "urlopen",
                          side_effect=[OSError("connection reset"), response]) as fetch, \
                patch.object(downloader.time, "sleep"), \
                patch.object(downloader.subprocess, "run", side_effect=AssertionError("curl")):
            self.assertEqual(self.run_download(), 0)
            self.assertEqual(fetch.call_count, 2)
        self.assertEqual((self.output / "installers/fixture.sh").read_bytes(), self.payload)

    def test_todesk_verification_page_is_rejected(self):
        self.app["url"] = "https://dl.todesk.com/linux/fixture.sh"
        response = io.BytesIO(b"<html>browser verification</html>" + b" " * 5000)
        response.url = self.app["url"]
        with patch.object(downloader.urllib.request, "urlopen", return_value=response):
            self.assertEqual(self.run_download(), 1)
        self.assertFalse((self.output / "manifest.json").exists())
        self.assertFalse(list(self.output.rglob("*.part")))

    def test_sunlogin_selects_deb_instead_of_default_rpm(self):
        data = {
            "versionno": "16.6", "downloadurl": "https://example.test/app.rpm",
            "downloadurlmultiple": [
                {"url": "https://example.test/app.rpm"},
                {"url": "https://example.test/app_amd64.deb"},
            ],
        }
        with patch.object(downloader, "fetch", return_value=json.dumps(data)):
            result = downloader.resolve({"resolver": "sunlogin"})
        self.assertTrue(result["url"].endswith("_amd64.deb"))

    def test_github_ambiguous_assets_fail(self):
        data = {"tag_name": "1", "assets": [
            {"name": "x_amd64.deb"}, {"name": "y_amd64.deb"},
        ]}
        with patch.object(downloader, "fetch", return_value=json.dumps(data)):
            with self.assertRaisesRegex(ValueError, "匹配 2"):
                downloader.resolve({"resolver": "github", "repo": "test/test", "asset_pattern": "amd64.deb"})

    def test_blender_patch_versions_sort_numerically(self):
        index = "blender-4.5.9-linux-x64.tar.xz blender-4.5.14-linux-x64.tar.xz"
        hashes = "a" * 64 + "  blender-4.5.14-linux-x64.tar.xz"
        with patch.object(downloader, "fetch", side_effect=[index, hashes]):
            result = downloader.resolve({"resolver": "blender", "series": "4.5"})
        self.assertEqual(result["version"], "4.5.14")

    def test_blender_follows_homepage_stable_release(self):
        page = (
            '<a href="https://www.blender.org/download/release/Blender5.2/'
            'blender-5.2.2-linux-x64.tar.xz/">Linux</a>'
            ' blender-5.3.0-beta-linux-x64.tar.xz'
            ' blender-5.2.2-linux-arm64.tar.xz'
        )
        hashes = "a" * 64 + "  blender-5.2.2-linux-x64.tar.xz"
        with patch.object(downloader, "fetch", side_effect=[page, hashes]):
            result = downloader.resolve({"resolver": "blender"})
        self.assertEqual(result["version"], "5.2.2")
        self.assertIn("/Blender5.2/", result["url"])

    def test_blender_missing_stable_link_fails(self):
        with patch.object(downloader, "fetch", return_value="maintenance"):
            with self.assertRaisesRegex(ValueError, "稳定版"):
                downloader.resolve({"resolver": "blender"})

    def test_sogou_selects_amd64_by_version_not_directory_timestamp(self):
        page = (
            r'https:\/\/ime-sec.gtimg.com/pc/dl/gzindex/999/sogoupinyin_4.2.9_amd64.deb '
            r'https://ime-sec.gtimg.com/pc/dl/gzindex/111/sogoupinyin_4.2.10_amd64.deb '
            r'https://ime-sec.gtimg.com/pc/dl/gzindex/222/sogoupinyin_5.0.0_arm64.deb'
        )
        with patch.object(downloader, "fetch", return_value=page):
            result = downloader.resolve({"resolver": "sogou", "homepage": "https://example.test"})
        self.assertEqual(result["version"], "4.2.10")
        self.assertTrue(result["filename"].endswith("_amd64.deb"))


if __name__ == "__main__":
    unittest.main()
