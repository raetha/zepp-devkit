# Plan: moving shared tooling here

Kestrel and the watch faces each carry copies of the same tooling, adapted at different times. They have already drifted (the faces' scheduled preview refresh reached Kestrel a day later; small fixes landed on one side only). Each step below moves one piece here, as a superset of both projects' versions, then switches both projects to it in one pull request each, with CI green before the next step.

| Step | Piece | Today in Kestrel | Today in the faces | Here |
| --- | --- | --- | --- | --- |
| 1 | Zepp preview upload, login, QR code, scheduled check | `tools/zeus_preview.sh`, `zeus_login.sh`, `zeus_preview_hook.cjs`, the `preview-check` job | the same, with small improvements | `preview/`, `preview-check/` (done) |
| 2 | DEV variants (registered DEV app ID, version stamp) | `tools/make_dev_variant.py` (one app) | `tools/make_dev_variant.py` (per face) | a script taking the project folder, the DEV ID and the build number |
| 3 | Releases from changelogs: check, plan, notes, "What's new" HTML | `tools/changelog.py`, `release_plan.py`, `release_notes.py` | the same, per face | a Python package (`zepp_devkit`) with the shared parts; each project keeps its install text |
| 4 | Packages: pick a `.zpk` from a `.zab` by device ID, one package per screen, the watch-model picker, `zpkd1://` QR codes | `tools/extract_zpk.py`, `packages.py`, `model_picker.py`, `make_qr.py` | `tools/extract_zpk.py`, `make_qr.py` | the package |
| 5 | The emulator: setup, install, tap/swipe/shot, the model sweep, Zeus behind a proxy | `tools/emu/`, `tools/compat/` | `tools/emu/`, `tools/harness/` | `emu/` (Node), as a command projects run |
| 6 | Store images: round 360×360 screenshots, 240×240 icon | `tools/store/assets.py` | (screenshots per face) | the package |

Stays in each project: install and test page layouts and wording, the faces' generator and harness, Kestrel's Home Assistant component and its tests, and what each project's store listing says.

How projects use it:
- **Actions** (`uses: raetha/zepp-devkit/<action>@<sha> # vX.Y.Z`) for CI steps.
- **The Python package and the emulator** from a pinned tag: `pip install "zepp-devkit @ git+https://github.com/raetha/zepp-devkit@vX.Y.Z"` in CI and in Claude sessions (attach this repo to the session when changing it).

Each step: build it here with tests, release (`vX.Y.Z`), switch Kestrel (from this session's repo access) and give the owner a prompt for the faces, update both projects' docs to point here, then delete their copies.
