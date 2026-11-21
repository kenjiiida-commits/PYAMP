#!/bin/sh
# PYAMP の DEB パッケージを作る
#   使い方:  ./packaging/build_deb.sh
#   できるもの: dist/pyamp_<バージョン>_all.deb
set -e
cd "$(dirname "$0")/.."
VERSION=$(cat VERSION)
BUILD=build/pyamp
rm -rf build
mkdir -p "$BUILD/DEBIAN" "$BUILD/usr/bin" "$BUILD/usr/share/pyamp" \
         "$BUILD/usr/share/applications" "$BUILD/usr/share/icons/hicolor/scalable/apps" \
         "$BUILD/usr/share/doc/pyamp" dist

sed "s/@VERSION@/$VERSION/" packaging/control.in > "$BUILD/DEBIAN/control"
install -m 755 packaging/prerm "$BUILD/DEBIAN/prerm"
install -m 755 packaging/pyamp-launcher.sh "$BUILD/usr/bin/pyamp"
install -m 644 pyamp/*.py "$BUILD/usr/share/pyamp/"
install -m 644 packaging/pyamp.desktop "$BUILD/usr/share/applications/"
install -m 644 pyamp/pyamp.svg "$BUILD/usr/share/icons/hicolor/scalable/apps/"
install -m 644 README.md LICENSE "$BUILD/usr/share/doc/pyamp/"

dpkg-deb --root-owner-group --build "$BUILD" "dist/pyamp_${VERSION}_all.deb"
echo "できました: dist/pyamp_${VERSION}_all.deb"
