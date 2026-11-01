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
`<name>-v<version>`; a component whose draft file exists is never released.
"""
import fnmatch
import json
from dataclasses import dataclass
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

    @property
    def tag(self):
        return f"{self.name}-v{self.version}"


def _read(root, spec, path, name=None, folder=None):
    data = json.loads((root / path).read_text())
    if "app" in data:  # Zeus app.json
        version, app_name = data["app"]["version"]["name"], data["app"]["appName"]
    else:  # Home Assistant manifest.json
        version, app_name = data["version"], data["name"]
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
