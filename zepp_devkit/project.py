"""A project's releasable components, from `zepp-devkit.json` at its root.

    {"components": [
      {"name": "watch", "app": "watch/app.json", "changelog": "watch/CHANGELOG.md",
       "draft": "watch/DRAFT", "title": "{app_name} watch app"},
      {"name": "ha", "manifest": "custom_components/kestrel/manifest.json",
       "changelog": "ha/CHANGELOG.md", "draft": "ha/DRAFT", "title": "{app_name} Home Assistant component"},
      {"each": "faces/*/app.json", "skip": ["*-dev"], "changelog": "{dir}/CHANGELOG.md",
       "draft": "{dir}/DRAFT", "title": "{app_name} {version}"}
    ]}

A component's version comes from a Zeus `app.json` (app.version.name, name app.appName) or
a Home Assistant `manifest.json` (version, name). With "each", every matching app.json is a
component named after its folder ({dir} is that folder, {name} its name). Tags are
`<name>-v<version>`, or the component's "tag" format (e.g. "v{version}"); a component whose
draft file exists is never released.

Parts that ship together under one version are one component: its "app" or "manifest" gives
the version, and "same_version" lists the other version files (app.json or manifest.json),
which must hold the same version:

    {"components": [
      {"name": "kestrel", "app": "watch/app.json",
       "same_version": ["custom_components/kestrel/manifest.json"],
       "changelog": "CHANGELOG.md", "draft": "DRAFT", "tag": "v{version}", "title": "{app_name} {version}"}
    ]}
"""
import fnmatch
import json
from dataclasses import dataclass, field
from pathlib import Path

CONFIG = "zepp-devkit.json"


@dataclass
class Component:
    name: str
    version: str
    app_name: str
    changelog: Path
    draft: bool
    title: str
    tag: str = ""
    others: dict = field(default_factory=dict)  # same_version: path -> the version it holds

    def __post_init__(self):
        self.tag = self.tag or f"{self.name}-v{self.version}"


def _version(root, path):
    """-> (version, app name) from a Zeus app.json or a Home Assistant manifest.json."""
    data = json.loads((root / path).read_text())
    if "app" in data:  # Zeus app.json
        return data["app"]["version"]["name"], data["app"]["appName"]
    return data["version"], data["name"]  # Home Assistant manifest.json


def _read(root, spec, path, name=None, folder=None):
    version, app_name = _version(root, path)
    name = name or spec["name"]
    fields = {"name": name, "dir": folder or "", "version": version, "app_name": app_name}
    fmt = lambda key, default="": str(spec.get(key, default)).format(**fields)  # noqa: E731
    draft = fmt("draft")
    return Component(
        name=name,
        version=version,
        app_name=app_name,
        changelog=root / fmt("changelog"),
        draft=bool(draft) and (root / draft).exists(),
        title=fmt("title", "{app_name} {version}"),
        tag=fmt("tag", "{name}-v{version}"),
        others={p: _version(root, p)[0] for p in spec.get("same_version", [])},
    )


def components(root="."):
    root = Path(root)
    spec = json.loads((root / CONFIG).read_text())
    out = []
    for c in spec["components"]:
        if "each" in c:
            for app in sorted(root.glob(c["each"])):
                folder = app.parent
                if any(fnmatch.fnmatch(folder.name, s) for s in c.get("skip", [])):
                    continue
                out.append(_read(root, c, app.relative_to(root), name=folder.name, folder=str(folder.relative_to(root))))
        else:
            out.append(_read(root, c, c.get("app") or c["manifest"]))
    return out


def component(name, root="."):
    for c in components(root):
        if c.name == name:
            return c
    raise SystemExit(f"no component {name!r} in {CONFIG}")
