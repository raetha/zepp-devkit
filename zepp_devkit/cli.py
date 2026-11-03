"""zepp-devkit: shared tooling for Zepp OS projects. Run from the project's folder.

  zepp-devkit dev-variant <src> <dst> --app-id N --build N [--sha S] [--ignore P ...] [--stamp FILE ...]
  zepp-devkit release-plan [--dev] [--github]       which components need a release (zepp-devkit.json)
  zepp-devkit changelog <component|CHANGELOG.md> <version> [--html]
  zepp-devkit notes <component|CHANGELOG.md> <version> [--install FILE] [--test-build N [--intro TEXT]]
  zepp-devkit extract-zpk <dist> <out.zpk> [--device-source N] [--device-zip out.zip]
  zepp-devkit packages <dist> <out dir> --prefix NAME   one .zpk per screen + packages.json
  zepp-devkit qr <out.png> <url> [--color #RRGGBB]
  zepp-devkit store-images <raw dir> <out dir> [--shape round|square] [--icon SRC.png]
  zepp-devkit preview <project> <out> --watches "A,B" [--label L] [--color C] [--github]
                                                       upload with the real zeus preview (ZEPP_* in env)
  zepp-devkit preview-check --build-result R [--failed TEXT] [--repositories TEXT]
  zepp-devkit emu <command> ...                        the emulator (zepp-devkit emu help)
  zepp-devkit path                                     where this package is installed
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _changelog_path(arg):
    """A component name (zepp-devkit.json) or a CHANGELOG.md path."""
    if arg.endswith(".md") or Path(arg).is_file():
        return Path(arg)
    from .project import component

    return component(arg).changelog


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["emu"]:  # straight through to the Node tool, in the project's folder
        node = os.environ.get("NODE", "node")
        return subprocess.call([node, str(HERE / "emu" / "emu.mjs"), *argv[1:]])

    ap = argparse.ArgumentParser(prog="zepp-devkit", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("dev-variant", help="a side-by-side DEV copy of a Zeus project")
    p.add_argument("src")
    p.add_argument("dst")
    p.add_argument("--app-id", required=True, type=int, help="the DEV app's ID, registered in the Zepp Console")
    p.add_argument("--build", required=True, type=int, help="build number: version code and -dev.N")
    p.add_argument("--sha", default="")
    p.add_argument("--ignore", nargs="*", default=[], help="more file patterns not to copy")
    p.add_argument("--stamp", nargs="*", default=[], help="files whose quoted version becomes the dev version")

    p = sub.add_parser("release-plan", help="which components need a release")
    p.add_argument("--github", action="store_true", help="also write releases=<json> to $GITHUB_OUTPUT")
    p.add_argument("--dev", action="store_true", help="a branch holding the expected next version: [Unreleased] is enough")

    p = sub.add_parser("changelog", help="print one version's section")
    p.add_argument("source")
    p.add_argument("version")
    p.add_argument("--html", action="store_true")

    p = sub.add_parser("notes", help="release notes: a changelog section plus install text")
    p.add_argument("source")
    p.add_argument("version")
    p.add_argument("--install", help="a markdown file with the install text ({version}, {name}, {tag} filled in)")
    p.add_argument("--test-build", type=int, help="notes for a dev pre-release with this run number")
    p.add_argument("--intro", default="", help="the first line of a dev pre-release's notes")

    p = sub.add_parser("extract-zpk", help="the .zpk for one watch out of dist/*.zab")
    p.add_argument("dist")
    p.add_argument("dest")
    p.add_argument("--device-source", type=int, default=None)
    p.add_argument("--device-zip")

    p = sub.add_parser("packages", help="one .zpk per screen and chip, plus packages.json")
    p.add_argument("dist")
    p.add_argument("dest")
    p.add_argument("--prefix", required=True)

    p = sub.add_parser("qr", help="a QR code for the Zepp app's scanner")
    p.add_argument("dest")
    p.add_argument("url")
    p.add_argument("--color", default="#14223A")

    p = sub.add_parser("store-images", help="Zepp store screenshots (and icon)")
    p.add_argument("raw")
    p.add_argument("out")
    p.add_argument("--shape", choices=["round", "square"], default="round")
    p.add_argument("--icon", help="a square logo PNG: writes <out>/icon.png at 240x240")

    p = sub.add_parser("preview", help="upload a Zeus project with the real zeus preview")
    p.add_argument("project")
    p.add_argument("out")
    p.add_argument("--watches", required=True, help='Zeus device names, comma-separated')
    p.add_argument("--label", default="")
    p.add_argument("--color", default="#14223A")
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("--github", action="store_true", help="write url, expires and failed to $GITHUB_OUTPUT; never fail")

    p = sub.add_parser("preview-check", help="fail a scheduled run whose previews didn't upload")
    p.add_argument("--build-result", required=True)
    p.add_argument("--failed", default="")
    p.add_argument("--repositories", default="this repository")

    sub.add_parser("path", help="where this package is installed")

    a = ap.parse_args(argv)
    if a.cmd == "dev-variant":
        from .devvariant import make_variant

        m = make_variant(a.src, a.dst, a.app_id, a.build, a.sha, a.ignore, a.stamp)
        print(f"{a.dst}: {m['appName']} {m['version']['name']} (appId {m['appId']})")
    elif a.cmd == "release-plan":
        from .release import plan, write_github_output

        releases, problems, lines = plan(dev=a.dev)
        print("\n".join(lines))
        if problems:
            print("\n".join(problems), file=sys.stderr)
            return 1
        if a.github:
            write_github_output(releases)
    elif a.cmd == "changelog":
        from .changelog import section, to_html

        body = section(_changelog_path(a.source), a.version)
        if body is None:
            print(f"no section for [{a.version}] in {_changelog_path(a.source)}", file=sys.stderr)
            return 1
        print(to_html(body) if a.html else body)
    elif a.cmd == "notes":
        from .release import notes

        install = ""
        if a.install:
            fields = {"version": a.version, "name": a.source, "tag": f"{a.source}-v{a.version}"}
            install = Path(a.install).read_text().format(**fields)
        print(notes(_changelog_path(a.source), a.version, install, a.test_build, a.intro))
    elif a.cmd == "extract-zpk":
        from .packages import BALANCE_3, extract

        name = extract(a.dist, a.dest, a.device_source or BALANCE_3, a.device_zip)
        print(f"wrote {a.dest}: {name} for deviceSource {a.device_source or BALANCE_3}")
    elif a.cmd == "packages":
        from .packages import split

        print(f"{len(split(a.dist, a.dest, a.prefix))} packages in {a.dest}")
    elif a.cmd == "qr":
        from .qr import make

        print(f"{make(a.dest, a.url, a.color)}  ->  {a.url}")
    elif a.cmd == "store-images":
        from .store import icon, screenshots

        for f in screenshots(a.raw, a.out, a.shape):
            print(f)
        if a.icon:
            print(icon(a.icon, Path(a.out) / "icon.png"))
    elif a.cmd == "preview":
        from .preview import upload

        return upload(a.project, a.out, a.watches, a.label, a.color, a.timeout, a.github)
    elif a.cmd == "preview-check":
        from .preview import check

        return check(a.build_result, a.failed, a.repositories)
    elif a.cmd == "path":
        print(HERE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
