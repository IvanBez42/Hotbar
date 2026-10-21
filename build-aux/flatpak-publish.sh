#!/bin/sh
# Add a release build to the self-hosted Flatpak repo served on GitHub Pages
# Usage: flatpak-publish.sh BUILD_REPO SITE_DIR
set -eu

build_repo=$1
site=$2
site_url=${SITE_URL:-https://ivanbez42.github.io/Hotbar}
repo=$site/repo
app_id=io.github.IvanBez42.Hotbar

# Git drops empty directories, so recreate the repo layout on every run
mkdir -p "$repo/objects" "$repo/refs/heads" "$repo/refs/mirrors" \
    "$repo/refs/remotes" "$repo/extensions" "$repo/state" "$repo/tmp"

# First release, create the config file
if [ ! -f "$repo/config" ]; then
    printf '[core]\nrepo_version=1\nmode=archive-z2\n' >"$repo/config"
fi

# Commit on top of the published release, so clients download small deltas
flatpak build-commit-from --gpg-sign="$GPG_KEY_ID" --src-repo="$build_repo" \
    "$repo" "app/$app_id/x86_64/master"

# Refresh the summary and appstream data that stores read, keeping a few old releases
flatpak build-update-repo --gpg-sign="$GPG_KEY_ID" \
    --title=Hotbar \
    --default-branch=master \
    --generate-static-deltas \
    --prune --prune-depth=3 \
    "$repo"

gpg --export "$GPG_KEY_ID" >"$site/hotbar.gpg"
key=$(base64 -w0 "$site/hotbar.gpg")

cat >"$site/$app_id.flatpakref" <<EOF
[Flatpak Ref]
Name=$app_id
Branch=master
Title=Hotbar
Url=$site_url/repo/
SuggestRemoteName=hotbar
RuntimeRepo=https://dl.flathub.org/repo/flathub.flatpakrepo
IsRuntime=false
GPGKey=$key
EOF

# Serve files as they are, without Jekyll processing
touch "$site/.nojekyll"
