# Ruijie RG-X30E Pro on ImmortalWrt 25.12

This branch adds source-level support for the MT7981B-based Ruijie RG-X30E Pro to ImmortalWrt `openwrt-25.12`. The device uses the existing combined NMBM/UBI layout and the installed Web U-Boot; this repository does not build or overwrite BL2/U-Boot.

## ImageBuilder versus source builds

ImageBuilder takes an already compiled kernel and package repository and assembles an image with selected packages and rootfs files. It is quick and suits package selection and small configuration overlays, but it cannot build a new kernel/device tree or add a target image definition on its own.

A source build compiles the kernel, device tree, packages, and target images from the ImmortalWrt source tree. This is the maintainable route for a board missing upstream: the DTS, image recipe, network defaults, and build configuration are kept as reviewed source changes. It takes more disk space and build time. Routine updates are merged from the upstream `openwrt-25.12` branch.

## Device-specific behavior

- The DTS describes the 256 MiB RAM, MT7981B, MT7531 switch, NAND partitions, three LAN ports (`lan1`–`lan3`), and the separate WAN port.
- Factory wireless calibration is read from this router's own read-only Factory partition through the device tree's NVMEM cells. No calibration dump or per-device backup is included in the repository or images.
- For bridged AP forwarding, this device build carries the open ImmortalWrt/OpenWrt 6.12 bridge-flow-offload patch series from [PR #22533](https://github.com/openwrt/openwrt/pull/22533). It enables bridge netfilter on `br-lan`, adds bridge-aware flow construction for PPE, and omits `bridger` so the two bridge acceleration paths do not compete. This is an experimental, not-yet-merged upstream kernel change; verify PPE `BND` entries and throughput/CPU behavior on hardware before treating it as a stable release.
- The factory UBI volume table reserves 750 LEBs for `rootfs_data`; a small preinit hook also repairs an oversized `rootfs_data` volume before it is mounted. This preserves the 19-PEB bad-block reserve verified on the device.
- The image includes LuCI, Argon, Simplified Chinese translations, and SFTP support. `CONFIG_LUCI_LANG_zh_Hans` is enabled explicitly in `config/x30e-pro.config`; without it `make defconfig` silently drops the `luci-i18n-*-zh-cn` packages and the UI falls back to English. The initial network configuration remains the upstream default for the board: LAN management at `192.168.1.1`, with the WAN separate. WAN/LAN MACs are derived from `product_info` (`ethaddr`, LAN = base+1) and the two Wi-Fi MACs from the same base (+2 for 2.4 GHz, +3 for 5 GHz), matching the stock firmware.
- Factory and sysupgrade images are generated. The factory image is for the existing Web U-Boot's `openwrt-firmware-combined` layout; sysupgrade is for an already running X30E Pro ImmortalWrt system.

## Build locally

Install the ImmortalWrt/OpenWrt host build prerequisites for your Linux distribution, then run:

```sh
sudo apt-get update
sudo apt-get install build-essential clang flex bison g++ gawk gcc-multilib g++-multilib \
  gettext git libncurses-dev libssl-dev python3-dev python3-setuptools python3-pyelftools \
  rsync swig time unzip zlib1g-dev file wget subversion libelf-dev zstd xsltproc
./scripts/build-x30e-pro.sh
```

The script updates/install feeds, selects `config/x30e-pro.config`, builds the full source tree, and validates the resulting image metadata and UBI volume table. It writes images and a validation JSON report under `bin/targets/mediatek/filogic/`. Set `JOBS=4` (or another safe value for your RAM) to control parallelism. The first build downloads dependencies and can require tens of gigabytes of free disk space.

To refresh from upstream manually:

```sh
git remote add upstream https://github.com/immortalwrt/immortalwrt.git
git fetch upstream openwrt-25.12
git merge --no-edit FETCH_HEAD
```

Resolve any conflicts as ordinary source changes, run the local build and checks, then commit and push. Never force-push over the upstream history.

## GitHub Actions

`.github/workflows/build.yml` builds on pushes to `openwrt-25.12`, on demand, and **daily**. A scheduled run merges ImmortalWrt `openwrt-25.12` before building; a manual run offers the same option. A merge conflict stops the job without overwriting the local adaptation. Successful runs upload factory/sysupgrade images, the manifest, checksums, and validation report as a 30-day Actions artifact.

Every successful build also **auto-publishes a rolling GitHub Release tagged `x30e-pro-latest`**: the factory/sysupgrade images, validation report, manifest and `sha256sums` are replaced with the newest build, so there is a stable download URL without release spam. A manual run with **Publish the successful build as a GitHub Release** additionally creates an immutable versioned release (`x30e-pro-build-<run>-<sha>`).

This repository is a standalone GitHub repository, **not a fork**, so the GitHub UI has no "Sync fork" button. The workflow keeps an `upstream` remote to `immortalwrt/immortalwrt` and merges `openwrt-25.12` automatically on the daily schedule (and on manual dispatch with *merge upstream* enabled), then pushes the merge; the resulting push triggers a normal build. Upstream changes therefore arrive without manual work, and conflicts fail the job without overwriting the branch.

The Actions build is a convenience and independent build check. Local source builds remain the primary validation path for this device. An offline image check cannot replace a hardware boot test.
