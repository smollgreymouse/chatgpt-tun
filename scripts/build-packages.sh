#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
VERSION="$(bash scripts/version.sh)"
if [[ "${GITHUB_REF_TYPE:-}" == "tag" && "${GITHUB_REF_NAME}" != "v${VERSION}" ]]; then
  echo "Tag ${GITHUB_REF_NAME} does not match pyproject.toml version ${VERSION}" >&2
  exit 1
fi
ARCH="$(dpkg --print-architecture)"
if [[ "$ARCH" != "amd64" ]]; then
  echo "Only amd64 builds are currently supported (got $ARCH)" >&2
  exit 1
fi
ROOT="$PWD/build/root"
DIST="$PWD/dist"
rm -rf "$PWD/build" "$DIST"
mkdir -p "$ROOT/opt/ctun/site" "$ROOT/usr/bin" "$DIST"
python3.12 -m pip install --no-compile --target "$ROOT/opt/ctun/site" .
cat > "$ROOT/usr/bin/ctun" <<'EOF'
#!/bin/sh
set -eu
export PYTHONPATH="/opt/ctun/site${PYTHONPATH:+:${PYTHONPATH}}"
exec python3.12 -m chatgpt_tun "$@"
EOF
chmod 755 "$ROOT/usr/bin/ctun"

# A tarball preserves the same system layout as the distro packages.
tar -C "$ROOT" -czf "$DIST/ctun_${VERSION}_linux_amd64.tar.gz" .

DEBROOT="$PWD/build/deb"
mkdir -p "$DEBROOT/DEBIAN"
cp -a "$ROOT/opt" "$ROOT/usr" "$DEBROOT/"
cat > "$DEBROOT/DEBIAN/control" <<EOF
Package: ctun
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: amd64
Maintainer: smollgreymouse
Depends: python3.12, ngrok
Description: Detached multi-project MCP gateway over ngrok
EOF
dpkg-deb --build --root-owner-group "$DEBROOT" "$DIST/ctun_${VERSION}_amd64.deb"

mkdir -p "$PWD/build/rpmbuild"/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
cat > "$PWD/build/rpmbuild/SPECS/ctun.spec" <<EOF
Name: ctun
Version: ${VERSION}
Release: 1
Summary: Detached multi-project MCP gateway over ngrok
License: MIT
BuildArch: x86_64
Requires: python3.12
Recommends: ngrok
%global debug_package %{nil}
%description
Detached multi-project MCP gateway for ChatGPT.
%prep
%build
%install
mkdir -p %{buildroot}
cp -a ${ROOT}/opt ${ROOT}/usr %{buildroot}/
%files
/opt/ctun
/usr/bin/ctun
/usr/bin/ctun
EOF
rpmbuild -bb --define "_topdir $PWD/build/rpmbuild" "$PWD/build/rpmbuild/SPECS/ctun.spec"
cp "$PWD/build/rpmbuild/RPMS/x86_64/"*.rpm "$DIST/"
sha256sum "$DIST"/* > "$DIST/SHA256SUMS"
echo "Built ${VERSION}:"
ls -lh "$DIST"
