# Changelog

All notable changes to the Zepp devkit. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/). Projects pin a commit of a release
(`uses: raetha/zepp-devkit/preview@<sha> # vX.Y.Z`), and Dependabot proposes updates.

## [Unreleased]

### Internal

- CI hardening: a single `CI passed` check gates releases, and no job keeps the workflow token on disk unless it pushes with git (`persist-credentials: false`).

## [0.1.0] - 2026-11-01

### Added

- `zepp-devkit`, a Python package and command, pinned once in a project's requirements:
  - `dev-variant`: a side-by-side DEV copy with a registered DEV app ID, the version `X.Y.Z-dev.N` and, optionally, that version stamped into other files.
  - `preview` and `preview-check`: upload with the real `zeus preview`, so the iPhone Zepp app lists the build under Developer Mode (and gives an app its Settings page); fail scheduled runs whose uploads failed, so an expired Zepp login gets noticed.
  - `release-plan`, `changelog` and `notes`: releases from Keep a Changelog files, for the components listed in `zepp-devkit.json`, and dev pre-release notes; `to_html()` for install pages.
  - `extract-zpk`, `packages` and `qr`: one watch's `.zpk`, one `.zpk` per screen with `packages.json`, `zpkd1://` QR codes; `picker()` for an install page's watch list.
  - `store-images`: the Zepp store's 360×360 screenshots (round or square) and 240×240 icon.
  - `emu`: the Zepp OS emulator for apps and watch faces.
- GitHub Actions wrapping it: `preview`, `preview-check` and `setup`.

Moved from raetha/zepp-kestrel and raetha/zepp-watch-faces, taking the better of each version.
