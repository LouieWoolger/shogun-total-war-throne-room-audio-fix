#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ctypes
import hashlib
import shutil
import sys
import time
from ctypes import wintypes
from pathlib import Path


PATCH_NAME = "Shogun Throne Audio Fix v2.0.0"
KNOWN_PATCHED_SHA256 = {
    "4445DCB123D595A9B68FD18A20B98A9F9332F9651474976636CB9EC54F3D16AF": "original",
    "A6CECD32946C10B152ADBC8D922BEAC8A67F7A639E6C4A10297297310C427285": "unit_fix_only",
    "11356636154934CC2FF2ED26B46FD82155C05EB52873FE6763F7FD22B1344D32": "original_plus_fix",
    "141C971763DC50AC2D5DD131E7FECAE87914C96FDB87B4EF25820E3B7A8C89DC": "unit_audio_fixes",
    "C7C3A70B5F281546F6A44F975EE795EE157D72A276007F983588F55EC88A9B89": "audio_harvest_fixes",
    "1154B5703769809D56B80DDB5B25BD98DEE2DED19721AEEFA9254D3EB81A9F78": "unit_audio_harvest_fixes",
}
BACKUP_SUFFIX = ".throne-room-audio-fix.bak"

PATCHES = [
    {
        "offset": 0x001B7CCB,
        "va": 0x005B7CCB,
        "original": bytes.fromhex("8B 4E 60 85 C9 74"),
        "patched": bytes.fromhex("E9 10 2F 16 00 90"),
        "label": "eoscheck entry -> code cave",
    },
    {
        "offset": 0x001B80D2,
        "va": 0x005B80D2,
        "original": bytes.fromhex("8A 45 18 84 C0 75 32"),
        "patched": bytes.fromhex("E9 49 2B 16 00 90 90"),
        "label": "duration scaling gate -> code cave",
    },
    {
        "offset": 0x001B7916,
        "va": 0x005B7916,
        "original": bytes.fromhex("8A 45 18 84 C0 74 07 B8 01 00 00 00 EB 05"),
        "patched": bytes.fromhex("E9 1C 33 16 00 90 90 90 90 90 90 90 90 90"),
        "label": "post-eof delay selection -> code cave",
    },
    {
        "offset": 0x0031ABE0,
        "va": 0x0071ABE0,
        "original": bytes(0x78),
        "patched": bytes.fromhex(
            "8B 4E 60 85 C9 75 34 8B 4E 54 85 C9 74 23 8D 44 "
            "24 10 50 51 8B 01 FF 50 20 85 C0 7C 14 8B 54 24 "
            "10 8B 7C 24 14 8B 46 40 8B 76 44 29 C2 19 F7 7C "
            "05 E9 E4 D0 E9 FF E9 EA D0 E9 FF E9 B2 D0 E9 FF "
            "83 7D 60 00 74 0C 8A 45 18 84 C0 75 05 E9 A7 D4 "
            "E9 FF E9 D4 D4 E9 FF 83 7D 60 00 74 07 8A 45 18 "
            "84 C0 74 0A B8 01 00 00 00 E9 DB CC E9 FF B8 88 "
            "13 00 00 E9 D1 CC E9 FF"
        ),
        "label": "stream timing code cave",
    },
    {
        "offset": 0x00198FA5,
        "va": 0x00598FA5,
        "original": bytes.fromhex("A9 FF 00 00 00 75 05 E8 2F F8 FF FF"),
        "patched": bytes.fromhex("E9 AE 1C 18 00 90 90 90 90 90 90 90"),
        "label": "script cleanup gate -> code cave",
    },
    {
        "offset": 0x0031AC58,
        "va": 0x0071AC58,
        "original": bytes(0x20),
        "patched": bytes.fromhex(
            "A9 FF 00 00 00 75 14 8B 0D 80 79 C9 00 85 C9 74 "
            "05 80 39 00 75 05 E8 6D DB E7 FF E9 39 E3 E7 FF"
        ),
        "label": "cleanup guard code cave",
    },
]

UNIT_PATCHES = [
    {
        "offset": 0x001364BC,
        "original": bytes.fromhex("A1 60 04 C7 00"),
        "patched": bytes.fromhex("B8 3C 00 00 00"),
        "label": "RecruitCostSizeScalar",
    },
    {
        "offset": 0x00135792,
        "original": bytes.fromhex("8B C6 83 C4 04 5E 5F C3 8B F6 90 90 90 90"),
        "patched": bytes.fromhex("E9 37 54 1E 00 90 90 90 90 90 90 90 90 90"),
        "label": "SupportCostSumTail",
    },
    {
        "offset": 0x0031ABCE,
        "original": bytes(18),
        "patched": bytes.fromhex("8B C6 6B C0 3C 99 F7 3D 60 04 C7 00 83 C4 04 5E 5F C3"),
        "label": "SupportCostCodeCave",
    },
    {
        "offset": 0x0015C550,
        "original": bytes.fromhex("83 F8 64"),
        "patched": bytes.fromhex("83 F8 7F"),
        "label": "TrainingTimeInitLoopCompare",
    },
    {
        "offset": 0x0015C57E,
        "original": bytes.fromhex("83 F8 64"),
        "patched": bytes.fromhex("83 F8 7F"),
        "label": "TrainingTimeInitLoopSpecialCompare",
    },
    {
        "offset": 0x0017CAEE,
        "original": bytes.fromhex("83 F8 64"),
        "patched": bytes.fromhex("83 F8 7F"),
        "label": "TrainingTimeInitUnrolledCompare",
    },
    {
        "offset": 0x001BFA08,
        "original": bytes.fromhex("83 FA 64"),
        "patched": bytes.fromhex("83 FA 7F"),
        "label": "TrainingTimeDoublePassACompare",
    },
    {
        "offset": 0x002E3213,
        "original": bytes.fromhex("83 F8 64"),
        "patched": bytes.fromhex("83 F8 7F"),
        "label": "TrainingTimeDoublePassBCompare",
    },
]

HARVEST_FRAME_ID_SETUP = bytes.fromhex(
    "33 C9 "
    "89 8C 24 80 02 00 00 "
    "89 8C 24 84 02 00 00 "
    "C7 84 24 88 02 00 00 0E 00 00 00 "
    "B8 0D 00 00 00 "
    "89 84 24 8C 02 00 00 "
    "89 84 24 90 02 00 00"
)

HARVEST_AUDIO_CAVE_TAIL = bytes.fromhex(
    "9C 60 8B 0D 1C 88 C2 00 85 "
    "C9 74 11 6A 01 E8 E6 D2 E2 FF C7 05 1C 88 C2 00 "
    "00 00 00 00 6A 68 E8 C4 15 FE FF 83 C4 04 85 C0 "
    "74 26 89 C6 31 D2 88 56 01 89 56 04 89 56 08 C6 "
    "46 0C 01 8D 94 24 64 02 00 00 52 89 F1 E8 AE D5 "
    "E9 FF 89 35 1C 88 C2 00 61 9D 31 C9 E9 A5 F0 E2 FF"
)

RESTORED_HARVEST_CODE_CAVE = HARVEST_FRAME_ID_SETUP + (b"\x90" * 9) + HARVEST_AUDIO_CAVE_TAIL

HARVEST_PATCHES = [
    {
        "offset": 0x00149D7F,
        "original": bytes.fromhex("60 32 F1 00"),
        "patched": bytes.fromhex("80 33 F1 00"),
        "label": "HarvestReportUseMp3Suffix",
    },
    {
        "offset": 0x00149D88,
        "original": HARVEST_FRAME_ID_SETUP,
        "patched": bytes.fromhex(
            "E9 F3 0E 1D 00 "
            "90 90 90 90 90 90 90 90 90 90 90 90 90 90 90 90 "
            "90 90 90 90 90 90 90 90 90 90 90 90 90 90 90 90 "
            "90 90 90 90 90 90 90 90 90"
        ),
        "label": "HarvestReportVoiceHook",
    },
    {
        "offset": 0x0031AC80,
        "original": bytes(0x91),
        "patched": RESTORED_HARVEST_CODE_CAVE,
        "label": "HarvestReportCodeCave",
    },
]

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
FILE_SHARE_DELETE = 0x00000004
OPEN_EXISTING = 3
FILE_BEGIN = 0
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def resolve_exe(target: str) -> Path:
    path = Path(target).expanduser().resolve()
    if path.is_dir():
        path = path / "ShogunM.exe"
    if not path.exists():
        raise FileNotFoundError(f"target not found: {path}")
    if path.name.lower() != "shogunm.exe":
        raise ValueError(f"target must be ShogunM.exe or its game folder: {path}")
    return path


def backup_path(exe: Path) -> Path:
    return exe.with_name(exe.name + BACKUP_SUFFIX)


def patch_state(data: bytes) -> tuple[int, int]:
    patched = 0
    clean = 0
    for patch in PATCHES:
        start = patch["offset"]
        end = start + len(patch["patched"])
        cur = data[start:end]
        if cur == patch["patched"]:
            patched += 1
        elif cur == patch["original"]:
            clean += 1
        else:
            raise RuntimeError(
                f"unsupported bytes at 0x{patch['offset']:08X}: {cur.hex(' ')}"
            )
    return patched, clean


def group_state(data: bytes, patches: list[dict]) -> str:
    states: list[str] = []
    for patch in patches:
        start = patch["offset"]
        end = start + len(patch["patched"])
        cur = data[start:end]
        if cur == patch["patched"]:
            states.append("patched")
        elif cur == patch["original"]:
            states.append("clean")
        else:
            states.append("unknown")

    unique = set(states)
    if "unknown" in unique:
        return "unknown"
    if unique == {"clean"}:
        return "clean"
    if unique == {"patched"}:
        return "patched"
    return "partial"


def combined_state(unit_state: str, audio_state: str, harvest_state: str) -> str:
    if "unknown" in {unit_state, audio_state, harvest_state} or "partial" in {unit_state, audio_state, harvest_state}:
        return "unknown_unsupported"
    if harvest_state == "patched" and audio_state != "patched":
        return "unknown_unsupported"
    if unit_state == "clean" and audio_state == "clean" and harvest_state == "clean":
        return "original"
    if unit_state == "patched" and audio_state == "clean" and harvest_state == "clean":
        return "unit_fix_only"
    if unit_state == "clean" and audio_state == "patched" and harvest_state == "clean":
        return "audio_fix_only"
    if unit_state == "patched" and audio_state == "patched" and harvest_state == "clean":
        return "unit_audio_fixes"
    if unit_state == "clean" and audio_state == "patched" and harvest_state == "patched":
        return "audio_harvest_fixes"
    if unit_state == "patched" and audio_state == "patched" and harvest_state == "patched":
        return "unit_audio_harvest_fixes"
    return "unknown_unsupported"


def create_file_shared(path: Path, access: int):
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateFileW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.LPVOID,
        wintypes.DWORD,
        wintypes.DWORD,
        wintypes.HANDLE,
    ]
    kernel32.CreateFileW.restype = wintypes.HANDLE

    last_error = 0
    for _ in range(80):
        handle = kernel32.CreateFileW(
            str(path),
            access,
            FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
            None,
            OPEN_EXISTING,
            0,
            None,
        )
        if handle != INVALID_HANDLE_VALUE:
            return kernel32, handle
        last_error = ctypes.get_last_error()
        if last_error != 32:
            raise ctypes.WinError(last_error)
        time.sleep(0.25)

    raise ctypes.WinError(last_error)


def write_shared(path: Path, writes: list[tuple[int, bytes]]) -> None:
    kernel32, handle = create_file_shared(path, GENERIC_READ | GENERIC_WRITE)
    kernel32.SetFilePointerEx.argtypes = [
        wintypes.HANDLE,
        ctypes.c_longlong,
        ctypes.POINTER(ctypes.c_longlong),
        wintypes.DWORD,
    ]
    kernel32.SetFilePointerEx.restype = wintypes.BOOL
    kernel32.WriteFile.argtypes = [
        wintypes.HANDLE,
        wintypes.LPCVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        wintypes.LPVOID,
    ]
    kernel32.WriteFile.restype = wintypes.BOOL
    kernel32.FlushFileBuffers.argtypes = [wintypes.HANDLE]
    kernel32.FlushFileBuffers.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    try:
        new_pos = ctypes.c_longlong()
        for offset, payload in writes:
            if not kernel32.SetFilePointerEx(handle, offset, ctypes.byref(new_pos), FILE_BEGIN):
                raise ctypes.WinError(ctypes.get_last_error())

            written = wintypes.DWORD()
            buf = (ctypes.c_ubyte * len(payload)).from_buffer_copy(payload)
            if not kernel32.WriteFile(
                handle,
                ctypes.cast(buf, wintypes.LPCVOID),
                len(payload),
                ctypes.byref(written),
                None,
            ):
                raise ctypes.WinError(ctypes.get_last_error())

            if written.value != len(payload):
                raise RuntimeError(
                    f"short write at 0x{offset:08X}: {written.value} != {len(payload)}"
                )

        if not kernel32.FlushFileBuffers(handle):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel32.CloseHandle(handle)


def chunk_writes(blob: bytes, chunk_size: int = 1 << 20) -> list[tuple[int, bytes]]:
    return [
        (offset, blob[offset : offset + chunk_size])
        for offset in range(0, len(blob), chunk_size)
    ]


def verify(exe: Path) -> int:
    data = exe.read_bytes()
    patched, clean = patch_state(data)
    audio_state = group_state(data, PATCHES)
    unit_state = group_state(data, UNIT_PATCHES)
    harvest_state = group_state(data, HARVEST_PATCHES)
    digest = sha256(exe)
    known_variant = KNOWN_PATCHED_SHA256.get(digest)

    print(f"name={PATCH_NAME}")
    print(f"target={exe}")
    print(f"sha256={digest}")
    print(f"patch_slots_patched={patched}")
    print(f"patch_slots_clean={clean}")
    print(f"known_patched_variant={known_variant if known_variant else 'no'}")
    print(f"combined_state={combined_state(unit_state, audio_state, harvest_state)}")
    print(f"unit_fix_present={'yes' if unit_state == 'patched' else 'no'}")
    print(f"harvest_restoration_fix_present={'yes' if harvest_state == 'patched' else 'no'}")
    if patched == len(PATCHES):
        print("status=patched")
    elif clean == len(PATCHES):
        print("status=clean_supported")
    else:
        print("status=mixed_supported")
    return 0


def apply_patch(exe: Path) -> int:
    data = exe.read_bytes()
    patched, _clean = patch_state(data)
    if patched == len(PATCHES):
        print("status=already_patched")
        print(f"sha256={sha256(exe)}")
        return 0

    backup = backup_path(exe)
    if not backup.exists():
        shutil.copy2(exe, backup)
        print(f"backup_created={backup}")
    else:
        print(f"backup_exists={backup}")

    writes: list[tuple[int, bytes]] = []
    for patch in PATCHES:
        start = patch["offset"]
        end = start + len(patch["patched"])
        cur = data[start:end]
        if cur == patch["patched"]:
            continue
        writes.append((start, patch["patched"]))
        print(
            f"patched {patch['label']} "
            f"file=0x{patch['offset']:08X} va=0x{patch['va']:08X}"
        )

    write_shared(exe, writes)
    print(f"sha256={sha256(exe)}")
    return 0


def restore(exe: Path) -> int:
    backup = backup_path(exe)
    if not backup.exists():
        raise FileNotFoundError(f"backup not found: {backup}")

    backup_bytes = backup.read_bytes()
    if exe.exists() and exe.stat().st_size == len(backup_bytes):
        write_shared(exe, chunk_writes(backup_bytes))
    else:
        shutil.copy2(backup, exe)
    print(f"restored_from={backup}")
    print(f"sha256={sha256(exe)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply or restore the direct binary fix for the Shogun throne-room audio cutoff."
    )
    parser.add_argument(
        "target",
        help="Path to ShogunM.exe or the game folder containing it.",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Only verify patch status and print hashes.",
    )
    parser.add_argument(
        "--restore",
        action="store_true",
        help="Restore ShogunM.exe from the backup created by this patcher.",
    )
    args = parser.parse_args()

    if args.verify and args.restore:
        parser.error("--verify and --restore cannot be used together")

    try:
        exe = resolve_exe(args.target)
        if args.verify:
            return verify(exe)
        if args.restore:
            return restore(exe)
        return apply_patch(exe)
    except Exception as exc:
        print(f"error={exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
