#!/usr/bin/env python3
"""Fix the X30E Pro factory UBI rootfs_data volume to preserve bad-block reserve."""

from pathlib import Path
import struct
import sys
import zlib

PEB_SIZE = 128 * 1024
VID_OFFSET = 2048
DATA_OFFSET = 4096
VTBL_VOL_ID = 0x7FFFEFFF
VTBL_RECORD_SIZE = 172
VTBL_CRC_OFFSET = 168
ROOTFS_DATA_VOL_ID = 2
ROOTFS_DATA_LEBS = 750


def crc(data: bytes) -> int:
    return zlib.crc32(data) ^ 0xFFFFFFFF


def fix_image(path: Path) -> None:
    image = bytearray(path.read_bytes())
    if len(image) % PEB_SIZE:
        raise ValueError(f"UBI image is not PEB-aligned: {len(image)}")

    patched = 0
    for peb in range(0, len(image), PEB_SIZE):
        vid = peb + VID_OFFSET
        if image[vid:vid + 4] != b"UBI!":
            continue
        if struct.unpack_from(">I", image, vid + 8)[0] != VTBL_VOL_ID:
            continue

        record = peb + DATA_OFFSET + ROOTFS_DATA_VOL_ID * VTBL_RECORD_SIZE
        name_len = struct.unpack_from(">H", image, record + 14)[0]
        name = bytes(image[record + 16:record + 16 + name_len])
        if name != b"rootfs_data":
            raise ValueError(f"unexpected volume {ROOTFS_DATA_VOL_ID}: {name!r}")

        old_reserved = struct.unpack_from(">I", image, record)[0]
        old_flags = image[record + 144]
        if old_reserved not in (9, ROOTFS_DATA_LEBS):
            raise ValueError(f"unexpected rootfs_data capacity: {old_reserved} LEBs")
        if old_flags not in (0, 1):
            raise ValueError(f"unexpected rootfs_data flags: {old_flags}")

        struct.pack_into(">I", image, record, ROOTFS_DATA_LEBS)
        image[record + 144] = 0  # fixed size, leaving 19 PEBs for UBI bad-block reserve
        struct.pack_into(">I", image, record + VTBL_CRC_OFFSET,
                         crc(bytes(image[record:record + VTBL_CRC_OFFSET])))
        patched += 1

    if patched != 2:
        raise ValueError(f"expected two UBI volume-table copies, patched {patched}")
    path.write_bytes(image)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} FACTORY_UBI_IMAGE")
    fix_image(Path(sys.argv[1]))
