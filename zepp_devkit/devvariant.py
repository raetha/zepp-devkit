"""A side-by-side test build of a Zeus project: a copy with its own app ID and a dev version.

The DEV app ID should be one registered in the Zepp Console (a "<Name> DEV" app): the
preview upload needs it, and only a preview gets the test build listed under the Zepp app's
Developer Mode. The copy installs next to the released app as "<Name> DEV", with the version
`<X.Y.Z>-dev.<build>` (the build number is also the version code, so each build is newer).
"""
import json
import shutil
from pathlib import Path

DEFAULT_IGNORE = ("dist", "__pycache__", "DRAFT")


def make_variant(src, dst, app_id, build, sha="", ignore=(), stamp=(), name_suffix=" DEV"):
    """Copy src to dst and make it the DEV build. stamp: files where the base version, quoted
    ('X.Y.Z' or "X.Y.Z"), becomes the dev version (e.g. a version module both halves report).
    Returns the new app.json's "app" object."""
    src, dst = Path(src), Path(dst)
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*DEFAULT_IGNORE, *ignore))
    app = json.loads((dst / "app.json").read_text())
    meta = app["app"]
    base = meta["version"]["name"]
    build = int(build)
    meta["appId"] = int(app_id)
    meta["appName"] = f"{meta['appName']}{name_suffix}"
    meta["version"] = {"code": build, "name": f"{base}-dev.{build}"}
    meta["description"] = f"Test build {build} {sha}".strip()
    for lang in app.get("i18n", {}).values():
        if "appName" in lang:
            lang["appName"] = f"{lang['appName']}{name_suffix}"
    (dst / "app.json").write_text(json.dumps(app, indent=2) + "\n")
    for rel in stamp:
        f = dst / rel
        text = f.read_text()
        new = text.replace(f"'{base}'", f"'{meta['version']['name']}'").replace(f'"{base}"', f'"{meta["version"]["name"]}"')
        if new == text:
            raise SystemExit(f"{f}: no quoted {base!r} to stamp (keep it equal to app.json's version)")
        f.write_text(new)
    return meta
