# Shogun: Total War Gold - Throne Room Audio Fix
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

Before patching, the script creates `ShogunM.exe.throne-room-audio-fix.bak` in the same folder. An existing backup is preserved.

The patch can be applied to a clean original, a unit-cost-patched executable, or one with the harvest report restoration fix already applied. All three patch sets touch different offsets and can be applied in any order. The harvest report restoration fix includes these audio bytes, so if that fix was applied first, this script will detect the audio fix as already present.

Known SHA-256 values:

```
11356636154934CC2FF2ED26B46FD82155C05EB52873FE6763F7FD22B1344D32  original + audio fix
141C971763DC50AC2D5DD131E7FECAE87914C96FDB87B4EF25820E3B7A8C89DC  unit-cost + audio fixes
C7C3A70B5F281546F6A44F975EE795EE157D72A276007F983588F55EC88A9B89  audio + harvest report fixes
1154B5703769809D56B80DDB5B25BD98DEE2DED19721AEEFA9254D3EB81A9F78  unit-cost + audio + harvest report fixes
```

If `--verify` reports `status=patched`, the fix is present and no changes are made. If it reports unsupported bytes, restore a clean `ShogunM.exe` first.
