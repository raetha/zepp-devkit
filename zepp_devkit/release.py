"""Releases from changelogs: which components need one, and their notes.

A component is released when its version has no `<name>-v<version>` git tag. Every
non-draft component's current version must have a changelog section, so a version bump
without notes fails CI (also on pull requests).
"""
import json
import os
import subprocess
from pathlib import Path

from .changelog import section
from .project import components


def plan(root="."):
    """-> (releases, problems, lines): releases as dicts for CI, problems that must fail it."""
    tags = set(subprocess.run(["git", "tag", "-l"], capture_output=True, text=True, cwd=root).stdout.split())
    releases, problems, lines = [], [], []
    for c in components(root):
        if c.draft:
            lines.append(f"{c.name}: draft, not released")
            continue
        if section(c.changelog, c.version) is None:
            problems.append(f"{c.changelog} needs a '## [{c.version}]' section (the version is {c.version})")
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
