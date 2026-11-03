"""Releases from changelogs: which components need one, and their notes.

A component is released when its version has no tag yet (`<name>-v<version>` unless it sets
its own format). Every non-draft component's current version must have a changelog section,
so a version bump without notes fails CI. With `dev`, for a branch that holds the expected
next version, an `[Unreleased]` section is enough: the release pull request names the
version's section, and CI on it (and on `main`) runs without `dev`.
"""
import json
import os
import subprocess
from pathlib import Path

from .changelog import section
from .project import components


def plan(root=".", dev=False):
    """-> (releases, problems, lines): releases as dicts for CI, problems that must fail it."""
    tags = set(subprocess.run(["git", "tag", "-l"], capture_output=True, text=True, cwd=root).stdout.split())
    releases, problems, lines = [], [], []
    for c in components(root):
        if c.draft:
            lines.append(f"{c.name}: draft, not released")
            continue
        for path, version in c.others.items():
            if version != c.version:
                problems.append(f"{path} has version {version}, but {c.name}'s version is {c.version}: they must match")
        if section(c.changelog, c.version) is None and not (dev and section(c.changelog, "Unreleased") is not None):
            wanted = f"'## [{c.version}]'" + (" or '## [Unreleased]'" if dev else "")
            problems.append(f"{c.changelog} needs a {wanted} section (the version is {c.version})")
        new = c.tag not in tags
        if new:
            releases.append({"component": c.name, "version": c.version, "tag": c.tag, "title": c.title})
        lines.append(f"{c.name}: version {c.version} -> {'RELEASE ' + c.tag if new else 'already released'}")
    return releases, problems, lines


def write_github_output(releases):
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"releases={json.dumps(releases)}\n")


def notes(changelog, version, install="", test_build=None, test_intro=""):
    """Release notes: the changelog section, then the install text (markdown) after a rule.
    With test_build: a dev pre-release's notes (the section is usually "Unreleased")."""
    body = section(changelog, version)
    if body is None:
        raise SystemExit(f"{changelog} has no section for [{version}]")
    if test_build is not None:
        body = body or "Nothing new since the last release yet."
        intro = test_intro or f"**Test build {test_build}**, for trying what's coming."
        return f"{intro}\n\n## Changes since the last release\n\n{body}"
    return f"{body}\n\n---\n\n{install.strip()}" if install.strip() else body


def read_text(path):
    return Path(path).read_text() if path else ""
