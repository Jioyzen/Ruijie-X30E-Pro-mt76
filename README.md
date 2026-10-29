# ImmortalWrt for Ruijie RG-X30E Pro

面向 **锐捷 RG-X30E Pro**（MT7981B）的 ImmortalWrt 25.12 源码级适配，使用 **mainline mt76** 无线驱动（不使用 MTK SDK 的 `mt_wifi`），保留原厂 U-Boot / 分区布局，支持 `sysupgrade` 与 U-Boot Web 恢复。

- 设备：Ruijie RG-X30E Pro
- SoC：MediaTek MT7981B + MT7976（AX3000，2.4G 2×2 + 5G 2×2）
- 内存 / 闪存：256 MB DDR3 / 128 MB Winbond SPI-NAND（NMBM + 单 UBI）
- 有线：MT7531 DSA，1× WAN + 3× LAN（千兆），CPU 口 2.5G
- 系统：ImmortalWrt 25.12-SNAPSHOT，Linux 6.12.112
- 无线：`mt7915e` + `mt7981-firmware`（mainline mt76），WED / PPE 硬件卸载

> 本仓库是独立仓库，不是 GitHub fork。上游同步通过 Actions 定时 merge 完成，见“上游同步”。

---

## 固件特性

- **mainline mt76**：`kmod-mt7915e` / `kmod-mt76` / `mt7981-wo-firmware`，双频 AP、WED、PPE 卸载。
- **桥接流卸载**：携带 OpenWrt 已审阅的 `675-01..07` 补丁（桥接 + IPv6 + MTK WDMA + VLAN），适合“所有口进 br-lan”的纯 AP 用法。
- **DSA 交换**：wan=p0、lan1=p1、lan2=p2、lan3=p4、cpu=p6@2500base-x。
- **NMBM + UBI**：与原厂 U-Boot 的 `openwrt-firmware-combined` 布局一致；`rootfs_data` 固定 750 LEB，保留 19 PEB 坏块余量。
- **校准与 MAC**：WiFi EEPROM 从本机 `Factory` 分区读取；WAN/LAN/2.4G/5G MAC 从 `product_info` 的 `ethaddr` 派生（WAN=base，LAN=base+1，2.4G=base+2，5G=base+3）。
- **LuCI**：Argon 主题 + 简体中文（`LUCI_LANG_zh_Hans`），默认语言 `zh_cn`。
- **升级保留配置**：`sysupgrade` 通过 `CI_ROOTFS_DATA_MAX=95232000` 正确 sizing `rootfs_data`，配置不再丢失。
- **安全更新**：dnsmasq 2.93-r2（含 2026-10 的 CVE 修复）。
- **生产默认值**：`ttylogin=1`、`log_size=512`、`min_cache_ttl=300`。
- **CI 自动发布**：每次成功构建自动更新 `x30e-pro-latest` Release。

---

## 下载

- **滚动 Release（推荐）**：<https://github.com/Jioyzen/Ruijie-X30E-Pro-mt76/releases/tag/x30e-pro-latest>
  - `*-squashfs-sysupgrade.bin`：系统内升级 / 已有 ImmortalWrt 使用
  - `*-squashfs-factory.bin`：U-Boot Web 恢复 / 首次刷写
  - `*-validation.json`、`*.manifest`、`sha256sums`
- **Actions Artifact**：每次构建保留 30 天（需要登录 GitHub 下载）
- **版本化 Release**：手动触发 workflow 并勾选 `publish_release` 时生成 `x30e-pro-build-<run>-<sha>`

---

## 刷机

### 方式 A：U-Boot Web 恢复（推荐首次刷写）

1. 断电，按住 RESET 上电，保持约 15 秒后松开
2. 电脑设为 `192.168.1.100/24`，网线接 LAN 口
3. 浏览器打开 `http://192.168.1.1`
4. 上传 `*-squashfs-factory.bin`，等待完成并重启

### 方式 B：系统内 sysupgrade

```sh
scp *-squashfs-sysupgrade.bin root@<路由器IP>:/tmp/sysupgrade.bin
ssh root@<路由器IP> 'sysupgrade -n /tmp/sysupgrade.bin'   # -n 不保留配置
# 或去掉 -n 保留 /etc/config
```

### 注意

- **不要写入 BL2 / FIP / FIP2 / Factory / product_info**；本适配只更新 UBI 内的 kernel/rootfs/rootfs_data。
- 首次刷机前建议完整备份 8 个 MTD 分区（尤其 `Factory` 校准分区）。
- 升级过程中不要断电。

---

## 首次启动

- 默认管理地址：`192.168.1.1`（LAN），root 密码为空
- 默认 WiFi：开放网络 `ImmortalWrt`（OpenWrt 默认）
- **请立即**：设置 root 密码、给 WiFi 设置 WPA2/WPA3 密码、按需修改 LAN IP
- 恢复出厂会回到上述默认状态（空密码 + 开放 WiFi），生产环境请先配置并保留配置备份

---

## 构建

依赖（Ubuntu/Debian）：

```sh
sudo apt-get install build-essential clang flex bison g++ gawk gcc-multilib g++-multilib \
  gettext git libncurses-dev libssl-dev python3-dev python3-setuptools python3-pyelftools \
  rsync swig time unzip zlib1g-dev file wget subversion libelf-dev zstd xsltproc
```

一键构建：

```sh
JOBS=4 ./scripts/build-x30e-pro.sh
```

脚本会：更新/安装 feeds → 应用 `config/x30e-pro.config` → `make defconfig` → 下载 → 编译 → 运行 `scripts/validate-x30e-pro.py`。

产物：`bin/targets/mediatek/filogic/`。

> 内存 ≤ 12 GB 建议 `JOBS=4`；`tools/llvm-bpf`（bridger/BPF）较吃内存，本配置已关闭 `bridger`。

手动构建：

```sh
./scripts/feeds update -a
./scripts/feeds install luci luci-theme-argon luci-app-argon-config \
  luci-i18n-base-zh-cn luci-i18n-argon-config-zh-cn \
  luci-i18n-firewall-zh-cn luci-i18n-package-manager-zh-cn openssh-sftp-server
cp config/x30e-pro.config .config
make defconfig
make -j4
python3 scripts/validate-x30e-pro.py
```

---

## 上游同步

本仓库不是 fork，因此网页上没有 “Sync fork” 按钮；同步由 CI 完成：

- 每周日 03:00 UTC（北京时间 11:00）自动：
  `git fetch upstream openwrt-25.12 && git merge FETCH_HEAD && git push`
- 手动触发 workflow 时勾选 `merge_upstream` 也会执行同样合并
- 合并冲突时任务失败且不会 push，分支保持原样
- 本地也可手动同步：

```sh
git remote add upstream https://github.com/immortalwrt/immortalwrt.git   # 只需一次
git fetch upstream openwrt-25.12
git merge FETCH_HEAD
```

> 同步对象是 **ImmortalWrt 的 `openwrt-25.12` 分支**，不是 OpenWrt 官方分支；ImmortalWrt 尚未合入的 OpenWrt 补丁需要单独 cherry-pick。

---

## CI 与发布

`.github/workflows/build.yml`：

- 触发：push 到 `openwrt-25.12`、每周定时、手动 `workflow_dispatch`
- 构建 + `validate-x30e-pro.py` 校验
- 上传 Artifact（30 天）
- **自动更新滚动 Release `x30e-pro-latest`**（5 个资产，clobber 覆盖，标记 Latest）
- 手动勾选 `publish_release` 时额外创建不可变版本化 Release

公开仓库的 GitHub-hosted Actions 分钟数免费；单次冷构建约 45–55 分钟。

---

## 适配与修复记录

- **DTS**：`target/linux/mediatek/dts/mt7981b-ruijie-rg-x30e-pro.dts`
  - 内存、SPI-NAND + NMBM、8 个固定分区、Factory eeprom nvmem、MT7531 DSA、LED/按键、WiFi。
- **镜像**：`target/linux/mediatek/image/filogic.mk`
  - `KERNEL_IN_UBI=1`、`factory.bin`（append-ubi + UBI 卷表修正）、`sysupgrade.bin`。
- **MAC**：
  - `files/etc/board.d/99_x30e-pro`：WAN=label，LAN=label+1
  - `files/etc/hotplug.d/ieee80211/99-x30e-pro-wifi-mac`：2.4G=+2，5G=+3
  - 修复了旧版把 `product_info` 的 17 字节 ASCII 当作 `mac-base` 导致 MAC 随机的问题。
- **中文 LuCI**：`config/x30e-pro.config` 显式 `CONFIG_LUCI_LANG_zh_Hans=y`；否则 `make defconfig` 会丢弃 `luci-i18n-*-zh-cn`。
- **升级保留配置**：`platform.sh` 设置 `CI_ROOTFS_DATA_MAX=95232000`；删除会在异常时清空 overlay 的 preinit UBI 钩子。
- **桥接卸载**：`675-01..07` 替换 review 前版本，补上 `skb_mac_header` 保护、IPv6 bridge dst、L2 泄漏修复。
- **dnsmasq**：2.93-r2，补齐 CVE-2026-93006/7/8/9/11、CNVD-C-2026-590208 等补丁。
- **默认值**：`ttylogin=1`、`log_size=512`、`min_cache_ttl=300`。

---

## 已知限制

- **无风扇、无有效温控绑定**：`pwm-fan` disabled，CPU 固定 1.3 GHz，仅 125 °C critical 关机；高温环境请保证散热并监控温度。
- **恢复出厂 = 空 root 密码 + 开放 WiFi + 192.168.1.1**：生产设备请先配置并保留备份。
- **默认 WPA2**：建议改为 WPA3/SAE + PMF，使用 20+ 位随机 PSK。
- **5G 160 MHz**：默认 ch48/HE160 会覆盖 DFS 信道（52–64），雷达事件可能触发切信道；覆盖优先可改 HE80。
- **内核 6.12.112**：如升级请直接 6.12.114，**跳过 6.12.113**（其 offload ct-timeout 改动会导致 WED 卸载流约 300 s 断流）。
- **包体偏大**：包含 PPP/odhcp6c/safexcel/fullcone 等当前未使用的包；重建时可裁剪。
- **无持久化日志**：logd 为 RAM 环（512 KB），重启即失；需要审计时接远程 syslog。

---

## 恢复与备份

- U-Boot Web failsafe：断电按住 RESET 上电 15 秒，电脑 `192.168.1.100/24`，访问 `http://192.168.1.1`
- 可上传 `factory.bin`（本固件）或原始 UBI 全盘备份恢复
- 建议首次刷机前备份：`BL2`、`u-boot-env`、`Factory`、`FIP`、`FIP2`、`product_info`、`kdump`、`ubi`
- `Factory` 是校准数据，丢失后无线可能无法正常校准

---

## 仓库结构

```
config/x30e-pro.config                 构建配置
files/                                 设备专用脚本（MAC、UI 默认值、桥接卸载 hotplug）
scripts/build-x30e-pro.sh              一键构建
scripts/validate-x30e-pro.py           镜像结构校验
scripts/x30e-pro-fix-ubi.py            factory 镜像 rootfs_data 卷表修正
target/linux/mediatek/dts/             DTS
target/linux/mediatek/image/filogic.mk 设备定义
target/linux/generic/pending-6.12/     桥接流卸载补丁 675-01..07
package/network/services/dnsmasq/      dnsmasq CVE 补丁
.github/workflows/build.yml            CI
```

---

## 致谢与许可

基于 [ImmortalWrt](https://github.com/immortalwrt/immortalwrt) / [OpenWrt](https://github.com/openwrt/openwrt)、Linux mt76、MediaTek ATF/U-Boot 以及社区桥接卸载补丁作者的工作。仓库代码遵循 GPL-2.0（与上游一致）。
