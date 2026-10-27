#!/usr/bin/env python3
"""Structural checks for X30E Pro output images. This does not test booting."""

from pathlib import Path
import hashlib
import json
import struct
import subprocess
import tarfile
import tempfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "bin/targets/mediatek/filogic"
matches = sorted(OUT.glob("immortalwrt-mediatek-filogic-ruijie_rg-x30e-pro-squashfs-factory.bin"))
assert len(matches) == 1, matches
FACTORY = matches[0]
PREFIX = FACTORY.name.removesuffix("-squashfs-factory.bin")
SYSUPGRADE = OUT / f"{PREFIX}-squashfs-sysupgrade.bin"
DTB = ROOT / "build_dir/target-aarch64_cortex-a53_musl/linux-mediatek_filogic/image-mt7981b-ruijie-rg-x30e-pro.dtb"

assert FACTORY.is_file(), FACTORY
assert SYSUPGRADE.is_file(), SYSUPGRADE
assert DTB.is_file(), DTB
assert len(FACTORY.read_bytes()) % (128 * 1024) == 0

with tarfile.open(SYSUPGRADE) as archive:
    members = archive.getnames()
    assert any(name.endswith("/CONTROL") for name in members)
    assert any(name.endswith("/kernel") for name in members)
    assert any(name.endswith("/root") for name in members)
    control = next(m for m in members if m.endswith("/CONTROL"))
    metadata = archive.extractfile(control).read().decode()
    assert "BOARD=ruijie_rg-x30e-pro" in metadata
    rootfs_image = archive.extractfile(next(m for m in members if m.endswith("/root"))).read()

with tempfile.TemporaryDirectory() as tempdir:
    metadata_path = Path(tempdir) / "sysupgrade-metadata.json"
    fwtool = ROOT / "staging_dir/host/bin/fwtool"
    subprocess.run([str(fwtool), "-i", str(metadata_path), str(SYSUPGRADE)], check=True)
    sysupgrade_metadata = json.loads(metadata_path.read_text())
    assert sysupgrade_metadata["supported_devices"] == ["ruijie,rg-x30e-pro"]

    rootfs_path = Path(tempdir) / "root.squashfs"
    rootfs_path.write_bytes(rootfs_image)
    unsquashfs = ROOT / "staging_dir/host/bin/unsquashfs4"
    assert unsquashfs.is_file(), unsquashfs
    def image_file(path: str) -> bytes:
        return subprocess.run([str(unsquashfs), "-cat", str(rootfs_path), path],
                              check=True, capture_output=True).stdout

    board_network = image_file("etc/board.d/02_network")
    assert b'ruijie,rg-x30e-pro)' in board_network
    assert b'ucidef_set_interfaces_lan_wan "lan1 lan2 lan3" "wan"' in board_network
    mac_script = image_file("etc/board.d/99_x30e-pro")
    assert b'mtd_get_mac_ascii product_info ethaddr' in mac_script
    assert b'ucidef_set_interface_macaddr "wan"' in mac_script
    assert b'ucidef_set_interface_macaddr "lan"' not in mac_script
    resize_hook = image_file("lib/preinit/76_x30e_fix_ubi_reserve")
    assert b'local target=750' in resize_hook
    assert b'ubimkvol /dev/ubi0 -n 2 -N rootfs_data -S "$target"' in resize_hook
    ui_defaults = image_file("etc/uci-defaults/99-x30e-pro-ui")
    assert b"/luci-static/argon" in ui_defaults and b"zh_cn" in ui_defaults
    bridge_hook = image_file("etc/hotplug.d/iface/99-x30e-bridge-netfilter")
    assert b'nf_call_iptables' in bridge_hook and b'nf_call_ip6tables' in bridge_hook
    flowtable_hook = image_file("etc/hotplug.d/net/99-x30e-flowtable-refresh")
    assert b'phy*-ap*' in flowtable_hook and b'/etc/init.d/firewall reload' in flowtable_hook
    upgrade_script = image_file("lib/upgrade/platform.sh")
    assert b"ruijie,rg-x30e-pro" in upgrade_script
    assert b'CI_UBIPART="ubi"' in upgrade_script

manifest = OUT / f"{PREFIX}.manifest"
packages = manifest.read_text().splitlines()
assert any(line.startswith("kmod-br-netfilter - ") for line in packages)
assert not any(line.startswith("bridger - ") for line in packages)

device_tree = (ROOT / "target/linux/mediatek/dts/mt7981b-ruijie-rg-x30e-pro.dts").read_text()
assert 'compatible = "ruijie,rg-x30e-pro"' in device_tree
# GPIO 54 is WF_HB8 on MT7981 and must not be reserved by the switch node.
assert "reset-gpios = <&pio 54" not in device_tree
for port in ('"wan"', '"lan1"', '"lan2"', '"lan3"'):
    assert f'label = {port}' in device_tree
assert 'label = "lan4"' not in device_tree

data = FACTORY.read_bytes()
copies = 0
for offset in range(0, len(data), 128 * 1024):
    vid = offset + 2048
    if data[vid:vid + 4] != b"UBI!" or struct.unpack_from(">I", data, vid + 8)[0] != 0x7FFFEFFF:
        continue
    record = offset + 4096 + 2 * 172
    assert struct.unpack_from(">I", data, record)[0] == 750
    assert data[record + 144] == 0
    assert struct.unpack_from(">I", data, record + 168)[0] == (zlib.crc32(data[record:record + 168]) ^ 0xFFFFFFFF)
    copies += 1
assert copies == 2, copies

report = {
    "offline_checks_passed": True,
    "boot_tested": False,
    "flash_written": False,
    "factory_image": FACTORY.name,
    "factory_size": FACTORY.stat().st_size,
    "factory_sha256": hashlib.sha256(data).hexdigest(),
    "sysupgrade_image": SYSUPGRADE.name,
    "sysupgrade_size": SYSUPGRADE.stat().st_size,
    "sysupgrade_sha256": hashlib.sha256(SYSUPGRADE.read_bytes()).hexdigest(),
    "rootfs_data_reserved_lebs": 750,
    "rootfs_data_autoresize_disabled": True,
    "rootfs_data_vtbl_copies_checked": copies,
    "calibration_source": "router Factory partition via device-tree nvmem at runtime; no device data bundled",
}
(OUT / f"{PREFIX}-validation.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
