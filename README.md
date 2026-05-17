# Shogun: Total War Gold - Throne Room Audio Fix
[![Downloads](https://img.shields.io/github/downloads/LouieWoolger/shogun-total-war-throne-room-audio-fix/total?style=for-the-badge)](https://github.com/LouieWoolger/shogun-total-war-throne-room-audio-fix/releases)
[![Release](https://img.shields.io/github/v/release/LouieWoolger/shogun-total-war-throne-room-audio-fix?style=for-the-badge)](https://github.com/LouieWoolger/shogun-total-war-throne-room-audio-fix/releases/latest)
[![Discord](https://img.shields.io/discord/1505490825889579018?style=for-the-badge&logo=discord&label=Discord&color=5865F2&cacheSeconds=300)](https://discord.gg/zKbDADqWRC)
[![Ko-fi](https://img.shields.io/badge/Ko--fi-Support-FF5F5F?style=for-the-badge&logo=ko-fi)](https://ko-fi.com/louiewoolger)

Fixes throne-room speech being cut off mid-sentence in Shogun: Total War Gold on modern Windows by patching `ShogunM.exe` directly. Advisor, emissary, and priest lines play to the end. The fix addresses two bugs: audio-only stream objects report end-of-stream too early, and the throne script can destroy the speech object before playback finishes.

Does not replace audio files, install a `dsound.dll` proxy, or modify anything outside `ShogunM.exe`. If you have a `dsound.dll` or `.mp3.wav` files from an older workaround, remove them before testing.

## Requirements

- Windows
- Python 3

## Usage

Pass the game folder or the path to `ShogunM.exe`:

```powershell
python .\shogun_throne_audio_fix.py "F:\Games\Shogun Total War Gold"
python .\shogun_throne_audio_fix.py "F:\Games\Shogun Total War Gold\ShogunM.exe"
```

Inspect without writing changes:

```powershell
python .\shogun_throne_audio_fix.py --verify "F:\Games\Shogun Total War Gold"
```

Restore from backup:

```powershell
python .\shogun_throne_audio_fix.py --restore "F:\Games\Shogun Total War Gold"
```

`--verify` and `--restore` cannot be combined.

## Notes

Before patching, the script creates `ShogunM.exe.bak` in the same folder. An existing backup is preserved.

The patch can be applied to a clean original or a unit-cost-patched executable. The two patch sets touch different offsets and can be applied in either order.

Known SHA-256 values:

```
11356636154934CC2FF2ED26B46FD82155C05EB52873FE6763F7FD22B1344D32  original + audio fix
141C971763DC50AC2D5DD131E7FECAE87914C96FDB87B4EF25820E3B7A8C89DC  unit-cost-patched + audio fix
```

If `--verify` reports `status=already_patched`, the fix is present and no changes are made. If it reports unsupported bytes, restore a clean `ShogunM.exe` first.
