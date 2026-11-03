# Changelog

All notable changes to the Zepp devkit. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/). Projects pin a commit of a release
(`uses: raetha/zepp-devkit/preview@<sha> # X.Y.Z`), and Dependabot proposes updates.

## [Unreleased]

### Changed

- Release tags no longer start with "v": a component's default tag is `<name>-<version>` (was `<name>-v<version>`), and this package's own releases are tagged `X.Y.Z` (pin `@0.3.0`, not `@v0.3.0`). A version that already has the older `v` tag counts as released, so nothing is released twice; a project with its own `tag` format gets the same check for that format with a "v" before the version.

## [0.2.0] - 2026-11-03

### Added

- `release-plan --dev`: on a `dev` branch that holds the expected next version, an `[Unreleased]` changelog section is enough; without `--dev` (on `main` and pull requests into it) the version still needs its own section.
- Components that ship together under one version: `same_version` in `zepp-devkit.json` lists other version files (Zeus `app.json` or Home Assistant `manifest.json`) that must hold the component's version, and `tag` sets the tag format (for example `v{version}`, one tag and GitHub release for the whole project).

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
