#!/bin/bash
# Build Emo Agent (single EXE/app + permission UI) for all platforms
set -e
cd "$(dirname "$0")"

OUT=../backend/agent_binaries
mkdir -p "$OUT"

VERSION="${1:-2.2.1}"
DEFAULT_BACKEND="${EMO_AGENT_DEFAULT_BACKEND:-}"

LDFLAGS="-s -w -X main.version=$VERSION"
if [ -n "$DEFAULT_BACKEND" ]; then
  LDFLAGS="$LDFLAGS -X main.defaultBackend=$DEFAULT_BACKEND"
fi

echo "Building Emo Agent v$VERSION → $OUT"
[ -n "$DEFAULT_BACKEND" ] && echo "Default backend: $DEFAULT_BACKEND"

if [ -f icon.ico ]; then
  if command -v rsrc >/dev/null 2>&1; then
    rsrc -ico icon.ico -o rsrc.syso -arch amd64
    rsrc -ico icon.ico -o rsrc_arm64.syso -arch arm64
  elif command -v go >/dev/null 2>&1; then
    GOBIN="$(go env GOPATH)/bin"
    export PATH="$GOBIN:$PATH"
    go install github.com/akavel/rsrc@latest
    rsrc -ico icon.ico -o rsrc.syso -arch amd64
    rsrc -ico icon.ico -o rsrc_arm64.syso -arch arm64
  fi
fi

build() {
  local goos=$1
  local goarch=$2
  local out=$3
  local extra=""
  if [ "$goos" = "windows" ]; then
    extra="-H windowsgui"
  fi
  echo "  → $goos/$goarch → $out"
  GOOS=$goos GOARCH=$goarch CGO_ENABLED=0 go build -ldflags "$LDFLAGS $extra" -o "$OUT/$out" .
}

build windows amd64 emo-agent-windows-amd64.exe
build windows arm64 emo-agent-windows-arm64.exe
build darwin amd64 emo-agent-macos-amd64
build darwin arm64 emo-agent-macos-arm64
build linux amd64 emo-agent-linux-amd64
build linux arm64 emo-agent-linux-arm64

echo "Done:"
ls -la "$OUT"
