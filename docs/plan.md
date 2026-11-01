# Plan: moving shared tooling here

Kestrel and the watch faces each carry copies of the same tooling, adapted at different times. They have already drifted (the faces' scheduled preview refresh reached Kestrel a day later; small fixes landed on one side only). Each step below moves one piece here, as a superset of both projects' versions, then switches both projects to it in one pull request each, with CI green before the next step.

| Step | Piece | Today in Kestrel | Today in the faces | Here |
| --- | --- | --- | --- | --- |
| 1 | Zepp preview upload, login, QR code, scheduled check | `tools/zeus_preview.sh`, `zeus_login.sh`, `zeus_preview_hook.cjs`, the `preview-check` job | the same, with small improvements | `zepp-devkit preview`, `preview-check` (done) |
| 2 | DEV variants (registered DEV app ID, version stamp) | `tools/make_dev_variant.py` (one app) | `tools/make_dev_variant.py` (per face) | `zepp-devkit dev-variant` (done) |
| 3 | Releases from changelogs: check, plan, notes, "What's new" HTML | `tools/changelog.py`, `release_plan.py`, `release_notes.py` | the same, per face | `release-plan`, `changelog`, `notes`, `to_html()` (done); each project keeps its install text |
| 4 | Packages: pick a `.zpk` from a `.zab` by device ID, one package per screen, the watch-model picker, `zpkd1://` QR codes | `tools/extract_zpk.py`, `packages.py`, `model_picker.py`, `make_qr.py` | `tools/extract_zpk.py`, `make_qr.py` | `extract-zpk`, `packages`, `qr`, `picker()` (done) |
| 5 | The emulator: setup, install, tap/swipe/shot, the model sweep, Zeus behind a proxy | `tools/emu/`, `tools/compat/` | `tools/emu/`, `tools/harness/` | `zepp-devkit emu` (done); the faces' screenshot and audit scripts and Kestrel's model sweep stay in each project for now |
| 6 | Store images: round 360×360 screenshots, 240×240 icon | `tools/store/assets.py` | (screenshots per face) | `store-images` (done) |

Stays in each project: install and test page layouts and wording, the faces' generator and harness, Kestrel's Home Assistant component and its tests, and what each project's store listing says.

How projects use it: one pin in `tools/requirements.txt` (`zepp-devkit @ git+https://github.com/raetha/zepp-devkit@<commit or tag>`), installed by CI and by Claude sessions alike, so both run the same commit. Attach this repository to a session when changing it. The GitHub Actions are there for projects that prefer `uses:`.

Later candidates: Kestrel's model sweep (`tools/compat/`, run the app on every watch model's emulator image) and the faces' screenshot tooling, once a second project needs them.

Each step: build it here with tests, release (`vX.Y.Z`), switch Kestrel (from this session's repo access) and give the owner a prompt for the faces, update both projects' docs to point here, then delete their copies.
