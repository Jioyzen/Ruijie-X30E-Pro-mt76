#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
JOBS="${JOBS:-4}"
cd "$ROOT"

./scripts/feeds update -a
./scripts/feeds install \
	luci luci-theme-argon luci-app-argon-config \
	luci-i18n-base-zh-cn luci-i18n-argon-config-zh-cn \
	luci-i18n-firewall-zh-cn luci-i18n-package-manager-zh-cn \
	openssh-sftp-server
cp config/x30e-pro.config .config
make defconfig
make download -j"$JOBS"
make -j"$JOBS"
python3 scripts/validate-x30e-pro.py

echo "Images and validation report are in bin/targets/mediatek/filogic/"
