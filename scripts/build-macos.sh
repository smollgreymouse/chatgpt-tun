#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
VERSION="$(bash scripts/version.sh)"
ARCH="$(uname -m)"
ROOT="$PWD/build/macos-root"
mkdir -p "$ROOT/opt/chatgpt-tun/site" "$ROOT/usr/local/bin" dist
python3.12 -m pip install --no-compile --target "$ROOT/opt/chatgpt-tun/site" .
cat > "$ROOT/usr/local/bin/ctun" <<'EOF'
#!/bin/sh
export PYTHONPATH="/opt/chatgpt-tun/site${PYTHONPATH:+:${PYTHONPATH}}"
exec python3.12 -m chatgpt_tun "$@"
EOF
chmod 755 "$ROOT/usr/local/bin/ctun"
ln -sf ctun "$ROOT/usr/local/bin/chatgpt-tun"
pkgbuild --root "$ROOT" --identifier "dev.smollgreymouse.chatgpt-tun" --version "$VERSION" --install-location / "dist/chatgpt-tun_${VERSION}_macos_${ARCH}.pkg"
