#!/usr/bin/env bash
# Tests for preview/zeus_preview.sh with a fake `zeus` (no network, no Zepp login):
# a good upload, an expired login, no QR code, and the login file left as it was.
#   bash test/preview.test.sh
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
export HOME="$tmp/home"; mkdir -p "$HOME/.zepp" "$tmp/bin" "$tmp/proj"
printf 'other="1"' > "$HOME/.zepp/.zeus"   # Zeus writes it without a final newline
export ZEPP_APPTOKEN="tok%3Dx" ZEPP_USERID="42" ZEPP_CNAME="api-mifit.example"
export PATH="$tmp/bin:$PATH" GITHUB_ACTIONS=""
fail() { echo "FAIL: $*"; exit 1; }

# fake zeus: checks it was called as `zeus preview -s -t <list>` with the login in place,
# then behaves as MODE says
cat > "$tmp/bin/zeus" <<'Z'
#!/usr/bin/env bash
[ "$1 $2 $3" = "preview -s -t" ] || { echo "bad args: $*"; exit 2; }
grep -q '^____user_zepp_com__token="tok=x"$' "$HOME/.zepp/.zeus" || { echo "login missing"; exit 2; }
grep -q '^other="1"$' "$HOME/.zepp/.zeus" || { echo "first line glued"; exit 2; }
case "$MODE" in
  ok) node -e "require('qrcode-terminal').generate('https://preview.example/qr?id=1')" ;;
  expired) echo "The login page has been opened in your browser" ;;
  *) echo "something else went wrong" ;;
esac
Z
chmod +x "$tmp/bin/zeus"
# a stand-in for Zeus's own qrcode-terminal module, which the hook wraps
mkdir -p "$tmp/node_modules/qrcode-terminal"
echo 'module.exports = { generate(url) { console.log("[QR for " + url + "]") } }' > "$tmp/node_modules/qrcode-terminal/index.js"
export NODE_PATH="$tmp/node_modules"

MODE=ok "$root/preview/zeus_preview.sh" "$tmp/proj" "$tmp/out" "Amazfit Balance 3,Amazfit Balance 3 Ti" demo > "$tmp/log"
[ "$(cat "$tmp/out/preview-url.txt")" = "https://preview.example/qr?id=1" ] || fail "url"
[ -s "$tmp/out/preview-qr.png" ] || fail "qr png"
grep -q "UTC" "$tmp/out/preview-expires.txt" || fail "expiry"
[ "$(cat "$HOME/.zepp/.zeus")" = 'other="1"' ] || fail "login file not restored"

if MODE=expired "$root/preview/zeus_preview.sh" "$tmp/proj" "$tmp/out2" "Amazfit Balance 3" demo > "$tmp/log" 2>&1; then fail "expired login succeeded"; fi
grep -q "login: it has expired" "$tmp/log" || fail "expired login not said"
if MODE=other "$root/preview/zeus_preview.sh" "$tmp/proj" "$tmp/out3" "Amazfit Balance 3" demo > "$tmp/log" 2>&1; then fail "no QR succeeded"; fi
grep -q "gave no QR code" "$tmp/log" || fail "missing QR not said"
[ "$(cat "$HOME/.zepp/.zeus")" = 'other="1"' ] || fail "login file not restored after a failure"
echo "preview: all tests passed"
