#!/usr/bin/env bash
# Upload a test build to Zepp's preview service with the real `zeus preview`: the only kind
# of install the iPhone Zepp app lists under Developer Mode (and gives an app's Settings
# page). Zeus builds the package itself, in preview mode (no intermediate products), for
# the given watches only. Used by the `preview` action (preview/action.yml).
#
#   zeus_preview.sh <project dir> <out dir> "<Zeus device names, comma-separated>" [label]
#
# Needs ZEPP_APPTOKEN, ZEPP_USERID and ZEPP_CNAME (zeus_login.sh). Writes
# <out>/preview-url.txt, preview-qr.png and preview-expires.txt. Exits 1, with an error
# annotation, when no preview was made (an expired login is said so).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
proj="$1"; out="$2"; devices="$3"; label="${4:-$(basename "$proj")}"
mkdir -p "$out"
# shellcheck source=zeus_login.sh
source "$here/zeus_login.sh"
log="$(mktemp)"
# no terminal: an expired login would wait for a browser forever, hence the timeout;
# a comma-separated -t list needs -s
(cd "$proj" && NODE_OPTIONS="--require $here/zeus_preview_hook.cjs" timeout "${ZEUS_TIMEOUT:-600}" zeus preview -s -t "$devices" </dev/null >"$log" 2>&1) || true
url="$(tr '\r' '\n' <"$log" | grep -o 'ZEUS_PREVIEW_URL=.*' | head -1 | cut -d= -f2- || true)"
if [ -z "$url" ]; then
  tr '\r' '\n' <"$log" | grep -v '^\s*$' | tail -15
  if grep -q "login page has been opened" "$log"; then
    echo "::error title=Zepp preview ($label)::Zepp refused the login: it has expired. Log in again and update ZEPP_APPTOKEN, ZEPP_USERID and ZEPP_CNAME in every repository that uses it."
  else
    echo "::error title=Zepp preview ($label)::zeus preview gave no QR code (log above)"
  fi
  rm -f "$log"
  exit 1
fi
rm -f "$log"
echo "$url" > "$out/preview-url.txt"
# Zeus says a preview's QR code is valid for 7 days
date -u -d '+7 days' '+%Y-%m-%d %H:%M UTC' > "$out/preview-expires.txt"
python3 "$here/qr.py" "$out/preview-qr.png" "$url" "${QR_COLOR:-#14223A}"
echo "preview uploaded ($label, $devices): expires $(cat "$out/preview-expires.txt")"
