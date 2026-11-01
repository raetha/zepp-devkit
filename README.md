# Zepp devkit

Shared build, test-build and publishing tooling for Zepp OS projects (Amazfit watches), so
the projects that use it behave the same and don't drift apart. MIT licensed.

Used by [zepp-kestrel](https://github.com/raetha/zepp-kestrel) and
[zepp-watch-faces](https://github.com/raetha/zepp-watch-faces). What moves in next, and in
what order, is in [docs/plan.md](docs/plan.md).

## What's here

| Path | What it is |
| --- | --- |
| `preview/` | A GitHub Action: upload a project with the real `zeus preview`, so the iPhone Zepp app lists it under Developer Mode, and write its QR code. |
| `setup/` | A GitHub Action that sets `ZEPP_DEVKIT` to the devkit's folder, for projects that call its scripts in a loop (one per watch face). |
| `preview-check/` | A GitHub Action for scheduled runs: fail when a preview didn't upload (an expired Zepp login). |
| `test/` | Tests for the scripts, with a fake Zeus (no network, no login). |

## Using it

Pin a commit, with the version in a comment, like any other action; Dependabot then proposes updates:

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
      # ... make the DEV variant (its own app ID, registered in the Zepp Console) ...
      - id: preview
        uses: raetha/zepp-devkit/preview@<sha> # vX.Y.Z
        env:
          ZEPP_APPTOKEN: ${{ secrets.ZEPP_APPTOKEN }}
          ZEPP_USERID: ${{ secrets.ZEPP_USERID }}
          ZEPP_CNAME: ${{ secrets.ZEPP_CNAME }}
        with:
          project: watch-dev
          out: out-dev/watch
          watches: Amazfit Balance 3,Amazfit Balance 3 Ti

  preview-check:
    needs: [build]
    if: always() && github.event_name == 'schedule'
    runs-on: ubuntu-24.04
    steps:
      - uses: raetha/zepp-devkit/preview-check@<sha> # vX.Y.Z
        with:
          failed: ${{ needs.build.outputs.preview_failed }}
          build-result: ${{ needs.build.result }}
```

`preview` writes `preview-url.txt`, `preview-qr.png` and `preview-expires.txt` into `out`, and never fails the step: when no preview was made (no login, an expired login, Zeus gave no QR code) its `failed` output says why, with an annotation. For several projects in one job (one per watch face), use `setup` once and call `"$ZEPP_DEVKIT/preview/zeus_preview.sh" <project> <out> "<watches>" [label]` in the loop (with the `ZEPP_*` env on that step): it exits 1 when no preview was made, and the loop collects the failures into the job's output for `preview-check`. Schedules run the default branch's copy of a workflow.

### What the preview does, and why

- Only a real `zeus preview` upload makes the iPhone Zepp app list a test build under Developer Mode, and give an app its Settings page. Our own `.zpk` QR codes (`zpkd1://…`) and a copy of Zeus's upload request (a normal all-watch build cut to one package) never did, under any app ID. `zeus preview` builds in preview mode for the chosen watches, without intermediate products.
- Give test builds their own app ID, registered in the [Zepp Console](https://console.zepp.com/) (a "<Name> DEV" app), not a made-up one.
- Zeus draws the QR code in the terminal but never prints its URL: `zeus_preview_hook.cjs`, preloaded with `NODE_OPTIONS=--require`, prints it. A comma-separated `-t` list needs `-s`; Zeus runs with `</dev/null` and a timeout, since an expired login waits for a browser forever.
- A preview's QR code is valid for 7 days; each upload makes a new one. Install it in the Zepp app: Profile → your watch → Developer Mode → + → Scan.
- On an iPhone, the Zepp app keeps the phone side (side service and settings page) of the first build it installed for an app ID, through later previews; only reinstalling the Zepp app replaces it. Watch faces have no phone side.

## The Zepp login

The actions need a Zepp developer login, as three repository secrets (**Settings → Secrets and variables → Actions**) in each repository that uses them: `ZEPP_APPTOKEN`, `ZEPP_USERID`, `ZEPP_CNAME`. One login serves every repository; when it expires, update them all. To get it, from any browser including a phone:

1. Open https://user.zepp.com/universalLogin/index.html#/login?project_name=zeppos_zeus_cli&platform_app=com.huami.webapp&project_redirect_uri=http%3A%2F%2Flocalhost%3A8765%2Flogin%2Fcallback and sign in with the Zepp developer account.
2. The browser then tries to open `http://localhost:8765/login/callback?apptoken=…&userid=…&cname=…` and fails to connect. That's expected: the address bar holds the values. Copy them into the three secrets (`apptoken` → `ZEPP_APPTOKEN`, `userid` → `ZEPP_USERID`, `cname` → `ZEPP_CNAME`; still URL-encoded is fine).

`cname` is a comma-separated list of the account's regional hosts; uploads go to the `api-mifit` one. When the token expires, runs say so ("Zepp refused the login"), and scheduled runs fail.

**Treat the token like a password.** In CI: `zeus_login.sh` writes it into Zeus's own login file (`~/.zepp/.zeus`, keys `____user_zepp_com__token`, `…__userid`, `…__cname`, after a newline, since Zeus writes that file without a final one) only while Zeus runs, and puts the file back after; the decoded values are masked in logs (`::add-mask::`); GitHub never gives secrets to pull requests from forks. Never paste the token into a chat or a sandbox. Never print the Zepp app's own log anywhere public (it holds apps' stored settings, tokens included), and never run `zeus bridge` in CI: once connected, it streams that log.

## Developing

`bash test/preview.test.sh` runs the preview script against a fake Zeus; CI also runs shellcheck. Work on `dev`; releases are pull requests into `main` (see `CLAUDE.md`).
