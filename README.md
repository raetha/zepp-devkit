# Zepp devkit

Shared build, test-build and publishing tooling for Zepp OS projects (Amazfit watches), so
the projects that use it behave the same and don't drift apart. MIT licensed.

Used by [zepp-kestrel](https://github.com/raetha/zepp-kestrel) and
[zepp-watch-faces](https://github.com/raetha/zepp-watch-faces). What moves in next, and in
what order, is in [docs/plan.md](docs/plan.md).

## What's here

| Path | What it is |
| --- | --- |
| `zepp_devkit/` | The Python package and its `zepp-devkit` command: DEV variants, Zepp previews, release plans and notes from changelogs, packages and QR codes, store images, and the emulator (`zepp_devkit/emu/`, Node). |
| `preview/`, `preview-check/`, `setup/` | GitHub Actions wrapping the command, for projects that would rather `uses:` them. |
| `tests/`, `test/` | Tests: the package (pytest) and the preview script against a fake Zeus (no network, no login). |
| `docs/plan.md` | What moved here from which project. |

## Using it

**Pin it once, in the project's Python requirements** (`tools/requirements.txt`), so CI and local sessions run the same commit:

```
zepp-devkit @ git+https://github.com/raetha/zepp-devkit@<commit or tag>
```

`pip install -r tools/requirements.txt` then gives the `zepp-devkit` command. Run it from the project's folder:

```
zepp-devkit dev-variant <src> <dst> --app-id N --build N [--sha S] [--ignore P ...] [--stamp FILE ...]
zepp-devkit preview <project> <out> --watches "Amazfit Balance 3,Amazfit Balance 3 Ti" [--label L] [--color C] [--github]
zepp-devkit preview-check --build-result R [--failed TEXT] [--repositories TEXT]
zepp-devkit release-plan [--github]
zepp-devkit changelog <component|CHANGELOG.md> <version> [--html]
zepp-devkit notes <component|CHANGELOG.md> <version> [--install FILE] [--test-build N [--intro TEXT]]
zepp-devkit extract-zpk <dist> <out.zpk> [--device-source N] [--device-zip out.zip]
zepp-devkit packages <dist> <out dir> --prefix NAME
zepp-devkit qr <out.png> <url> [--color #RRGGBB]
zepp-devkit store-images <raw dir> <out dir> [--shape round|square] [--icon logo.png]
zepp-devkit emu <setup|start|stop|install <dir>|apps|shot|tap|swipe|key|set|face|enable-aod|save-base|reset|rest> ...
```

Python code can import it too (`from zepp_devkit.changelog import section, to_html`, `from zepp_devkit.packages import picker`), for the parts that stay in each project: its pages and install texts.

**`zepp-devkit.json`** at the project's root lists its releasable components, for `release-plan`, `changelog` and `notes` (see `zepp_devkit/project.py`):

```json
{"components": [
  {"name": "watch", "app": "watch/app.json", "changelog": "watch/CHANGELOG.md", "draft": "watch/DRAFT", "title": "{app_name} watch app"},
  {"each": "faces/*/app.json", "skip": ["*-dev"], "changelog": "{dir}/CHANGELOG.md", "draft": "{dir}/DRAFT", "title": "{app_name} {version}"}
]}
```

Tags are `<name>-v<version>`; a component whose draft file exists is never released; every other component's version needs a changelog section, or `release-plan` fails.

### In GitHub Actions

With the requirements pinned, CI runs the command after `pip install -r tools/requirements.txt`:

```yaml
on:
  push:
    branches: [main, dev]
  schedule:
    - cron: "17 9 */5 * *"   # previews expire after 7 days: refresh every 5

jobs:
  build:
    outputs:
      preview_failed: ${{ steps.preview.outputs.failed }}
    steps:
      # ... pip install -r tools/requirements.txt; zepp-devkit dev-variant ... ; zeus build ...
      - id: preview
        env:
          ZEPP_APPTOKEN: ${{ secrets.ZEPP_APPTOKEN }}
          ZEPP_USERID: ${{ secrets.ZEPP_USERID }}
          ZEPP_CNAME: ${{ secrets.ZEPP_CNAME }}
        run: zepp-devkit preview watch-dev out-dev/watch --watches "Amazfit Balance 3,Amazfit Balance 3 Ti" --github

  preview-check:
    needs: [build]
    if: always() && github.event_name == 'schedule'
    runs-on: ubuntu-24.04
    steps:
      # ... checkout and pip install -r tools/requirements.txt
      - run: zepp-devkit preview-check --build-result "${{ needs.build.result }}" --failed "${{ needs.build.outputs.preview_failed }}"
```

`preview --github` writes `url`, `expires` and `failed` to the step's outputs and never fails the step: when no preview was made (no login, an expired login, Zeus gave no QR code) `failed` says why, with an annotation, and the project's page falls back to its own codes. Several uploads in one step (one per watch face) append to `failed`. `preview-check` then fails scheduled runs, so an expired login gets noticed. Schedules run the default branch's copy of a workflow.

Projects that would rather not install it can use the actions, pinned to a commit: `raetha/zepp-devkit/preview@<sha>` (inputs `project`, `out`, `watches`, `label`, `qr-color`; outputs `url`, `expires`, `failed`), `raetha/zepp-devkit/preview-check@<sha>` (`failed`, `build-result`, `repositories`), and `raetha/zepp-devkit/setup@<sha>` (installs the command at that commit).

### The emulator

`zepp-devkit emu` runs Zepp's QEMU emulator with the real firmware (the Balance 2 image), headless. It keeps its files in `<project>/tools/.emu/` (ignore it in git), needs the `ws` npm package in the project, and, on Linux x86_64, `libvte-2.91-0`, `libaio1t64`, `xvfb`, `xdotool` and Zeus. `zepp-devkit emu setup` downloads it (about 240 MB, from `*.zepp.com` and `*.huami.com`), `start` boots it, `install <dir>` builds and installs an app or watch face (a folder with `app.json`, or its name one level down, as in `faces/<face>`), and `shot`, `tap`, `swipe`, `key`, `set` drive it. Zepp's images can't be decoded by the emulator, so `install` swaps the source PNGs back in. Each project documents its own quirks (screen timeout, buttons, which sensors are fed).

### What the preview does, and why

- Only a real `zeus preview` upload makes the iPhone Zepp app list a test build under Developer Mode, and give an app its Settings page. Our own `.zpk` QR codes (`zpkd1://…`) and a copy of Zeus's upload request (a normal all-watch build cut to one package) never did, under any app ID. `zeus preview` builds in preview mode for the chosen watches, without intermediate products.
- Give test builds their own app ID, registered in the [Zepp Console](https://console.zepp.com/) (a "<Name> DEV" app), not a made-up one.
- Zeus draws the QR code in the terminal but never prints its URL: `zepp_devkit/preview/zeus_preview_hook.cjs`, preloaded with `NODE_OPTIONS=--require`, prints it. A comma-separated `-t` list needs `-s`; Zeus runs with `</dev/null` and a timeout, since an expired login waits for a browser forever.
- A preview's QR code is valid for 7 days; each upload makes a new one. Install it in the Zepp app: Profile → your watch → Developer Mode → + → Scan.
- On an iPhone, the Zepp app keeps the phone side (side service and settings page) of the first build it installed for an app ID, through later previews; only reinstalling the Zepp app replaces it. Watch faces have no phone side.

### Updating, and trying devkit changes in a project

Projects pin a release tag (`@v0.1.0`). To update, change the pin in `tools/requirements.txt` (Dependabot may propose it). To try a devkit change before it's released, push it to this repository's `dev` and, on a branch of the project, pin that commit (`@<sha>`); the project's pull request then runs its CI against it. Projects don't follow this repository's `dev` branch directly: a moving reference would change their builds without a commit of their own, and a broken devkit `dev` would break every project at once.

## The Zepp login

The actions need a Zepp developer login, as three repository secrets (**Settings → Secrets and variables → Actions**) in each repository that uses them: `ZEPP_APPTOKEN`, `ZEPP_USERID`, `ZEPP_CNAME`. One login serves every repository; when it expires, update them all. To get it, from any browser including a phone:

1. Open https://user.zepp.com/universalLogin/index.html#/login?project_name=zeppos_zeus_cli&platform_app=com.huami.webapp&project_redirect_uri=http%3A%2F%2Flocalhost%3A8765%2Flogin%2Fcallback and sign in with the Zepp developer account.
2. The browser then tries to open `http://localhost:8765/login/callback?apptoken=…&userid=…&cname=…` and fails to connect. That's expected: the address bar holds the values. Copy them into the three secrets (`apptoken` → `ZEPP_APPTOKEN`, `userid` → `ZEPP_USERID`, `cname` → `ZEPP_CNAME`; still URL-encoded is fine).

`cname` is a comma-separated list of the account's regional hosts; uploads go to the `api-mifit` one. When the token expires, runs say so ("Zepp refused the login"), and scheduled runs fail.

**Treat the token like a password.** In CI: `zepp_devkit/preview/zeus_login.sh` writes it into Zeus's own login file (`~/.zepp/.zeus`, keys `____user_zepp_com__token`, `…__userid`, `…__cname`, after a newline, since Zeus writes that file without a final one) only while Zeus runs, and puts the file back after; the decoded values are masked in logs (`::add-mask::`); GitHub never gives secrets to pull requests from forks. Never paste the token into a chat or a sandbox. Never print the Zepp app's own log anywhere public (it holds apps' stored settings, tokens included), and never run `zeus bridge` in CI: once connected, it streams that log.

## Developing

`pip install -e . pytest && pytest -q tests` and `bash test/preview.test.sh` (the preview script against a fake Zeus); CI also runs shellcheck. Work on `dev`; releases are pull requests into `main` (see `CLAUDE.md`).
