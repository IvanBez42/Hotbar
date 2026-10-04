#!/bin/sh
# Build the development Flatpak and install it for the current user.
set -eu

cd "$(dirname "$0")/.."
manifest=flatpak/io.github.IvanBez42.Hotbar.Devel.json
log=.flatpak-builder/last-build.log
mkdir -p .flatpak-builder

notify() {
    command -v notify-send >/dev/null && notify-send -a Hotbar -i io.github.IvanBez42.Hotbar.Devel "$@" || true
}

if flatpak-builder --user --install --force-clean _build "$manifest" 2>&1 | tee "$log"; then
    notify "Hotbar rebuilt" "Installed $(git rev-parse --short HEAD 2>/dev/null || echo 'working tree')"
else
    notify -u critical "Hotbar build failed" "See $PWD/$log"
    exit 1
fi
