#!/bin/sh
# Build a Flatpak and install it for the current user.
# Usage: flatpak-install.sh [devel|release]
#   devel   (default) builds the working tree as io.github.IvanBez42.Hotbar.Devel
#   release builds the local main branch as io.github.IvanBez42.Hotbar
set -eu -o pipefail

cd "$(dirname "$0")/.."

case "${1:-devel}" in
    devel)
        app_id=io.github.IvanBez42.Hotbar.Devel
        builddir=_build
        rev=$(git rev-parse --short HEAD 2>/dev/null || echo 'working tree')
        ;;
    release)
        app_id=io.github.IvanBez42.Hotbar
        builddir=_build-release
        rev="main@$(git rev-parse --short main)"
        ;;
    *)
        echo "usage: $0 [devel|release]" >&2
        exit 2
        ;;
esac

manifest=flatpak/$app_id.json
log=.flatpak-builder/last-build.log
mkdir -p .flatpak-builder

notify() {
    command -v notify-send >/dev/null && notify-send -a Hotbar -i "$app_id" "$@" || true
}

if flatpak-builder --user --install --install-deps-from=flathub --force-clean "$builddir" "$manifest" 2>&1 | tee "$log"; then
    notify "Hotbar rebuilt" "Installed $app_id ($rev)"
else
    notify -u critical "Hotbar build failed" "See $PWD/$log"
    exit 1
fi
