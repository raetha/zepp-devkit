# Changelog

All notable changes to the Zepp devkit. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/). Projects pin a commit of a release
(`uses: raetha/zepp-devkit/preview@<sha> # vX.Y.Z`), and Dependabot proposes updates.

## [Unreleased]

### Added

- `preview`: upload a Zepp OS project with the real `zeus preview`, so the iPhone Zepp app lists it under Developer Mode (and gives an app its Settings page), and write its QR code, URL and expiry. A failed upload is a warning, reported in its `failed` output. From raetha/zepp-kestrel and raetha/zepp-watch-faces.
- `setup`: sets `ZEPP_DEVKIT` for projects that call the scripts in a loop (one per watch face), and installs Zeus and the QR tools.
- `preview-check`: fails a scheduled run when a preview didn't upload, so an expired Zepp login gets noticed.
