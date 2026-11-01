"""Zepp previews: upload a Zeus project with the real `zeus preview`, and check scheduled runs.

Only a real `zeus preview` upload makes the iPhone Zepp app list a test build under
Developer Mode (and give an app its Settings page); see the README. The work is done by
zeus_preview.sh (with zeus_login.sh and zeus_preview_hook.cjs), next to this file.
"""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOGIN = ("ZEPP_APPTOKEN", "ZEPP_USERID", "ZEPP_CNAME")


def _github_output(**values):
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            for k, v in values.items():
                f.write(f"{k}={v}\n")


def upload(project, out, watches, label="", colour="#14223A", timeout=600, github=False):
    """Upload; -> 0 when the preview was made. With github: outputs url/expires/failed, and
    0 even on failure (a warning: the caller's page falls back; preview-check fails schedules)."""
    label = label or Path(project).name
    if not all(os.environ.get(k) for k in LOGIN):
        print(f"No ZEPP_* login: no preview upload for {label}")
        if github:
            _github_output(failed=f"{label}: no ZEPP_* secrets")
            return 0
        return 1
    env = {**os.environ, "QR_COLOR": colour, "ZEUS_TIMEOUT": str(timeout), "PYTHON": sys.executable}
    ok = subprocess.call(["bash", str(HERE / "zeus_preview.sh"), str(project), str(out), watches, label], env=env) == 0
    if github:
        if ok:
            _github_output(url=(Path(out) / "preview-url.txt").read_text().strip(),
                           expires=(Path(out) / "preview-expires.txt").read_text().strip())
        else:
            print(f"::warning title=Zepp preview ({label})::upload failed (see the annotation above)")
            _github_output(failed=f"{label}: the preview upload failed")
        return 0
    return 0 if ok else 1


def check(build_result, failed="", repositories="this repository"):
    """For scheduled runs that keep previews valid (they expire after 7 days): -> 1 when the
    build failed or a preview didn't upload, so GitHub emails the owner."""
    if build_result != "success":
        print("::error title=Zepp preview::the build failed, so the test builds weren't refreshed")
        return 1
    if failed.strip():
        print(f"::error title=Zepp preview::{failed.strip()}. If the log says the login expired, get new values "
              f"(zepp-devkit README -> \"The Zepp login\") and update ZEPP_APPTOKEN, ZEPP_USERID and ZEPP_CNAME in {repositories}.")
        return 1
    print("previews refreshed")
    return 0
