"""Tests for the zepp_devkit package (no network, no Zeus)."""
import io
import json
import subprocess
import zipfile

import pytest
from PIL import Image

from zepp_devkit import changelog, cli, devvariant, packages, project, release, store

CHANGELOG = """# Changelog

## [Unreleased]

- Something coming.

## [1.1.0] - 2026-10-30

The second release.

### Added

- **Bold** thing with `code` and a [link](https://example.com).
  Continued on the next line.

## [1.0.0] - 2026-10-01

- First.
"""


def app_json(path, name="Demo", version="1.1.0", app_id=1000, app_type="app", i18n=True):
    path.mkdir(parents=True, exist_ok=True)
    data = {"app": {"appId": app_id, "appName": name, "appType": app_type, "version": {"code": 3, "name": version}}}
    if i18n:
        data["i18n"] = {"en-US": {"appName": name}}
    (path / "app.json").write_text(json.dumps(data))
    return path


def test_dev_variant(tmp_path):
    src = app_json(tmp_path / "watch")
    (src / "lib").mkdir()
    (src / "lib" / "version.js").write_text("export const BUILD = '1.1.0'\n")
    (src / "dist").mkdir()
    (src / "DRAFT").write_text("")
    (src / "docs").mkdir()
    meta = devvariant.make_variant(src, tmp_path / "watch-dev", 1134161, 42, "abc1234", ignore=["docs"], stamp=["lib/version.js"])
    dst = tmp_path / "watch-dev"
    assert meta["appId"] == 1134161 and meta["appName"] == "Demo DEV"
    assert meta["version"] == {"code": 42, "name": "1.1.0-dev.42"} and meta["description"] == "Test build 42 abc1234"
    app = json.loads((dst / "app.json").read_text())
    assert app["i18n"]["en-US"]["appName"] == "Demo DEV"
    assert "'1.1.0-dev.42'" in (dst / "lib" / "version.js").read_text()
    assert not (dst / "dist").exists() and not (dst / "DRAFT").exists() and not (dst / "docs").exists()
    (src / "lib" / "other.js").write_text("export const X = 1\n")
    with pytest.raises(SystemExit):  # a stamp file without the version is an error, not silently skipped
        devvariant.make_variant(src, tmp_path / "other", 1, 1, stamp=["lib/other.js"])


def test_changelog_sections_and_html(tmp_path):
    f = tmp_path / "CHANGELOG.md"
    f.write_text(CHANGELOG)
    assert changelog.section(f, "Unreleased") == "- Something coming."
    assert changelog.section(f, "1.0.0") == "- First."
    assert changelog.section(f, "9.9.9") is None
    html = changelog.to_html(changelog.section(f, "1.1.0"))
    assert "<p>The second release.</p>" in html and "<h4>Added</h4>" in html
    assert "<strong>Bold</strong>" in html and "<code>code</code>" in html and '<a href="https://example.com">link</a>' in html
    assert "Continued on the next line." in html.split("<li>")[1]


def git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def test_release_plan_components_and_notes(tmp_path, monkeypatch):
    app_json(tmp_path / "watch", name="Kestrel", version="1.1.0")
    (tmp_path / "watch" / "CHANGELOG.md").write_text(CHANGELOG)
    (tmp_path / "ha").mkdir()
    (tmp_path / "ha" / "CHANGELOG.md").write_text("## [Unreleased]\n\n- x\n")
    (tmp_path / "ha" / "DRAFT").write_text("")
    (tmp_path / "custom_components" / "kestrel").mkdir(parents=True)
    (tmp_path / "custom_components" / "kestrel" / "manifest.json").write_text(json.dumps({"name": "Kestrel", "version": "0.1.0"}))
    for face, v in (("sextant", "1.0.0"), ("twisted", "2.0.0")):
        app_json(tmp_path / "faces" / face, name=face.title(), version=v, app_type="watchface")
        (tmp_path / "faces" / face / "CHANGELOG.md").write_text(CHANGELOG)
    app_json(tmp_path / "faces" / "sextant-dev", version="1.0.0-dev.1")  # a DEV copy: skipped
    (tmp_path / project.CONFIG).write_text(json.dumps({"components": [
        {"name": "watch", "app": "watch/app.json", "changelog": "watch/CHANGELOG.md", "draft": "watch/DRAFT", "title": "{app_name} watch app"},
        {"name": "ha", "manifest": "custom_components/kestrel/manifest.json", "changelog": "ha/CHANGELOG.md", "draft": "ha/DRAFT"},
        {"each": "faces/*/app.json", "skip": ["*-dev"], "changelog": "{dir}/CHANGELOG.md", "draft": "{dir}/DRAFT", "title": "{app_name} {version}"},
    ]}))
    git(tmp_path, "init", "-q")
    git(tmp_path, "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-q", "--allow-empty", "-m", "x")
    git(tmp_path, "tag", "sextant-v1.0.0")

    names = [c.name for c in project.components(tmp_path)]
    assert names == ["watch", "ha", "sextant", "twisted"]
    assert project.component("ha", tmp_path).draft
    releases, problems, lines = release.plan(tmp_path)
    # twisted's 2.0.0 has no changelog section: that's a problem; sextant is already tagged; ha is a draft
    assert [r["component"] for r in releases] == ["watch", "twisted"]
    assert releases[0] == {"component": "watch", "version": "1.1.0", "tag": "watch-v1.1.0", "title": "Kestrel watch app"}
    assert problems == [f"{tmp_path / 'faces/twisted/CHANGELOG.md'} needs a '## [2.0.0]' section (the version is 2.0.0)"]
    assert "ha: draft, not released" in lines

    out = tmp_path / "out"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    release.write_github_output(releases)
    assert json.loads(out.read_text().split("=", 1)[1])[0]["tag"] == "watch-v1.1.0"

    cl = tmp_path / "watch" / "CHANGELOG.md"
    assert release.notes(cl, "1.0.0", "**Install** it.") == "- First.\n\n---\n\n**Install** it."
    test = release.notes(cl, "Unreleased", test_build=7)
    assert test.startswith("**Test build 7**") and "- Something coming." in test
    (tmp_path / "empty.md").write_text("## [Unreleased]\n\n## [1.0.0]\n\n- x\n")
    assert "Nothing new since the last release yet." in release.notes(tmp_path / "empty.md", "Unreleased", test_build=1)

    # the command line, from the project's folder
    monkeypatch.chdir(tmp_path)
    (tmp_path / "install.md").write_text("Install {name} {version} ({tag}).")
    assert cli.main(["release-plan"]) == 1  # twisted's missing section fails it


def fake_zab(path):
    """A .zab with two packages: round 480 (Balance 3) and square."""
    def zpk(sources):
        dev = io.BytesIO()
        with zipfile.ZipFile(dev, "w") as d:
            d.writestr("app.json", json.dumps({"platforms": [{"deviceSource": s} for s in sources]}))
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w") as z:
            z.writestr("device.zip", dev.getvalue())
        return out.getvalue()

    with zipfile.ZipFile(path, "w") as zab:
        zab.writestr("a.zpk", zpk([11141376, 11145475]))
        zab.writestr("b.zpk", zpk([8519936]))
        zab.writestr("manifest.json", json.dumps({"zpks": [
            {"name": "a.zpk", "platforms": [{"screenType": "round", "screenResolution": "480x480", "cpuPlatform": "ZPS"}]},
            {"name": "b.zpk", "platforms": [{"screenType": "square", "screenResolution": "390x450", "cpuPlatform": "NXP"}]},
        ]}))


def test_packages_and_picker(tmp_path):
    (tmp_path / "dist").mkdir()
    fake_zab(tmp_path / "dist" / "x.zab")
    assert packages.extract(tmp_path / "dist", tmp_path / "one.zpk", 11145475, tmp_path / "dev.zip") == "a.zpk"
    assert zipfile.ZipFile(tmp_path / "dev.zip").namelist() == ["app.json"]
    with pytest.raises(SystemExit):
        packages.extract(tmp_path / "dist", tmp_path / "no.zpk", 1)
    index = packages.split(tmp_path / "dist", tmp_path / "pk", "demo")
    assert index == {
        "demo-r480-zps.zpk": {"screen": "round 480x480", "chip": "ZPS", "sources": [11141376, 11145475]},
        "demo-s390x450-nxp.zpk": {"screen": "square 390x450", "chip": "NXP", "sources": [8519936]},
    }
    models = [
        {"name": "Balance 3", "sources": [11141376], "status": "tested"},
        {"name": "Bip", "sources": [8519936], "status": "emulator"},
        {"name": "Old", "sources": [1], "status": "unsupported"},
    ]
    page = packages.picker(tmp_path / "pk", "example.github.io/x/pk", models)
    assert 'value="demo-r480-zps.zpk"' in page and " selected" in page and "Old" not in page
    assert (tmp_path / "pk" / "qr-demo-r480-zps.png").exists()


def test_store_images(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    Image.new("RGB", (480, 480), (255, 0, 0)).save(raw / "1-home.png")
    Image.new("RGB", (390, 450), (0, 255, 0)).save(tmp_path / "sq.png")
    (shot,) = store.screenshots(raw, tmp_path / "out")
    im = Image.open(shot)
    assert im.size == (360, 360) and im.getpixel((0, 0))[3] == 0 and im.getpixel((180, 180))[3] == 255
    sq = Image.open(store.screenshot(tmp_path / "sq.png", tmp_path / "sq-out.png", "square"))
    assert sq.size == (360, 360) and sq.getpixel((0, 180))[3] == 0 and sq.getpixel((180, 0))[3] == 255
    Image.new("RGBA", (1024, 1024), (1, 2, 3, 255)).save(tmp_path / "logo.png")
    assert Image.open(store.icon(tmp_path / "logo.png", tmp_path / "icon.png")).size == (240, 240)


def test_cli_qr_and_changelog(tmp_path, capsys):
    assert cli.main(["qr", str(tmp_path / "q.png"), "zpkd1://example/x.zpk"]) == 0
    assert (tmp_path / "q.png").exists()
    (tmp_path / "CHANGELOG.md").write_text(CHANGELOG)
    assert cli.main(["changelog", str(tmp_path / "CHANGELOG.md"), "1.0.0"]) == 0
    assert capsys.readouterr().out.strip().endswith("- First.")
    (tmp_path / "install.md").write_text("Get {version}.")
    assert cli.main(["notes", str(tmp_path / "CHANGELOG.md"), "1.0.0", "--install", str(tmp_path / "install.md")]) == 0
    assert capsys.readouterr().out.strip().endswith("Get 1.0.0.")


def test_preview_without_login_and_the_check(tmp_path, monkeypatch, capsys):
    from zepp_devkit import preview

    for k in preview.LOGIN:
        monkeypatch.delenv(k, raising=False)
    out = tmp_path / "gh"
    monkeypatch.setenv("GITHUB_OUTPUT", str(out))
    assert cli.main(["preview", str(tmp_path), str(tmp_path / "o"), "--watches", "Amazfit Balance 3", "--label", "Demo DEV"]) == 1
    assert cli.main(["preview", str(tmp_path), str(tmp_path / "o"), "--watches", "Amazfit Balance 3", "--label", "Demo DEV", "--github"]) == 0
    assert out.read_text() == "failed=Demo DEV: no ZEPP_* secrets\n"
    assert preview.check("success") == 0
    assert preview.check("failure") == 1
    assert preview.check("success", "Demo DEV: the preview upload failed", "a and b") == 1
    assert "update ZEPP_APPTOKEN, ZEPP_USERID and ZEPP_CNAME in a and b" in capsys.readouterr().out
