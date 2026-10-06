#!/usr/bin/env bash
# Evidence browser for local goal runs: Chrome for Testing (ADR 0036, C3-04 / QA-RV3-04).
#
#   bash scripts/dev-chrome.sh          # install (idempotent) and print the version
#   bash scripts/dev-chrome.sh check    # exit 0 only if the pinned build is installed
#
# Installs CfT 141.0.7390.54 (linux64) at /opt/google/chrome, where Playwright's `chrome` channel
# looks; evidence runs then set PW_CHROMIUM_CHANNEL=chrome. The zip is sha256-checked before it is
# unpacked; a mismatch, a failed download or a wrong version inside the zip installs nothing.
# A matching install is left untouched; any other version is replaced.
#
# Env (tests only): CHROME_DIR, CHROME_ZIP_URL, CHROME_SHA256.
set -euo pipefail

CHROME_VERSION="141.0.7390.54"
# sha256 of chrome-linux64.zip for 141.0.7390.54, recorded in ADR 0036 (2026-10-06)
DEFAULT_SHA256="5023ec2b8995b74caa5de0e22d5e30f871c3ecce67a6e52d3c9f9dfed423ed01"
DEFAULT_URL="https://storage.googleapis.com/chrome-for-testing-public/141.0.7390.54/linux64/chrome-linux64.zip"

DEST="${CHROME_DIR:-/opt/google/chrome}"
URL="${CHROME_ZIP_URL:-$DEFAULT_URL}"
SHA256="${CHROME_SHA256:-$DEFAULT_SHA256}"
WANT="Google Chrome for Testing $CHROME_VERSION"

die() { echo "dev-chrome: $*" >&2; exit 1; }

installed_version() {
  [[ -x "$DEST/chrome" ]] || return 1
  "$DEST/chrome" --version 2>/dev/null | sed 's/[[:space:]]*$//'
}

if [[ "${1:-install}" == "check" ]]; then
  v="$(installed_version)" || die "not installed at $DEST (run: bash scripts/dev-chrome.sh)"
  [[ "$v" == "$WANT" ]] || die "wrong version at $DEST: '$v' (want '$WANT')"
  echo "$v"
  exit 0
fi
[[ "${1:-install}" == "install" ]] || die "usage: dev-chrome.sh [install|check]"

if [[ "$(installed_version || true)" == "$WANT" ]]; then
  echo "dev-chrome: $WANT already installed at $DEST" >&2
  echo "$WANT"
  exit 0
fi

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

echo "dev-chrome: downloading $WANT" >&2
curl -fsSL -o "$work/chrome.zip" "$URL" || die "download failed: $URL"
echo "$SHA256  $work/chrome.zip" | sha256sum -c --quiet - >/dev/null 2>&1 \
  || die "sha256 mismatch for $URL; refusing to install it"

python3 -c 'import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])' \
  "$work/chrome.zip" "$work/x"
new="$work/x/chrome-linux64"
[[ -f "$new/chrome" ]] || die "zip has no chrome-linux64/chrome"
chmod +x "$new/chrome"
# zipfile drops the exec bit of helper binaries too; restore it on the known ones.
for f in chrome_crashpad_handler chrome_sandbox chrome-wrapper; do
  [[ -f "$new/$f" ]] && chmod +x "$new/$f"
done
got="$("$new/chrome" --version 2>/dev/null | sed 's/[[:space:]]*$//' || true)"
[[ "$got" == "$WANT" ]] || die "version inside the zip is '$got', want '$WANT'"

mkdir -p "$(dirname "$DEST")"
rm -rf "$DEST"
mv "$new" "$DEST"
echo "dev-chrome: installed at $DEST; evidence runs set PW_CHROMIUM_CHANNEL=chrome" >&2
"$DEST/chrome" --version
