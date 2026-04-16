# Shogun: Total War Gold - Throne Room Audio Fix v2.0.0

Direct binary patch for the throne-room speech cutoff bug in `ShogunM.exe`.

This fixes the advisor/emissary/priest speech being cut off partway through in the throne room on modern systems, without:

- `dsound.dll` proxies
- `.mp3.wav` sidecar files
- runtime wrappers
- replacing the game audio assets

The fix patches the game executable directly.

## What This Fix Changes

The throne-room speech bug turned out to be two separate executable bugs:

1. Audio-only AMStream objects were treated as end-of-stream too early.
2. The paired throne script object could still destroy the live speech object before playback had actually finished.

This release fixes both in `ShogunM.exe` by:

- using stream time for the no-video/no-sample speech path instead of returning EOF immediately
- skipping the incorrect `*8/6` duration scaling for that same path
- removing the broken `5000 ms` post-EOF linger on that path
- delaying the throne script cleanup until the active speech object has really gone inactive

## Files

- `shogun_throne_audio_fix.py`
  Applies the patch, verifies the patch state, or restores from backup.
- `README.md`
  This file.

## Requirements

- Windows
- Python 3

## Usage

Patch the game:

```powershell
python .\shogun_throne_audio_fix.py "F:\Games\Shogun Total War Gold"
```

You can also pass the EXE directly:

```powershell
python .\shogun_throne_audio_fix.py "F:\Games\Shogun Total War Gold\ShogunM.exe"
```

Verify patch status:

```powershell
python .\shogun_throne_audio_fix.py --verify "F:\Games\Shogun Total War Gold"
```

Restore the backup created by the patcher:

```powershell
python .\shogun_throne_audio_fix.py --restore "F:\Games\Shogun Total War Gold"
```

## Backup And Rollback

The patcher creates:

```text
ShogunM.exe.bak
```

in the same folder as `ShogunM.exe`.

To roll back, either:

- run `--restore`
- or copy the `.bak` file back over `ShogunM.exe`

## Verification In Game

1. Remove any older workaround files first if you still have them:
   - `dsound.dll`
   - generated `.mp3.wav` files
2. Launch the patched `ShogunM.exe`.
3. Go to the throne room.
4. Click the advisor, emissary, or priest.
5. Confirm the speech now plays to the real end of the line instead of cutting off early.

## Supported Target

This patcher is intentionally strict.

It supports the `ShogunM.exe` build whose patch locations match the expected original bytes at the offsets listed below. If your EXE has already been modified by some other patch, the script will refuse to patch it rather than guessing.

Known final patched SHA-256 values:

```text
11356636154934CC2FF2ED26B46FD82155C05EB52873FE6763F7FD22B1344D32  original GOG/Steam EXE + audio fix
141C971763DC50AC2D5DD131E7FECAE87914C96FDB87B4EF25820E3B7A8C89DC  cost-fix-patched EXE + audio fix
```

The patch does not need the unit-cost patch to work.

It patches only the throne-audio code paths listed below, and those offsets do not overlap the unit-cost patch offsets. So it can be applied to:

- a clean original GOG/Steam `ShogunM.exe`
- a `ShogunM.exe` that already has the unit-cost patch

## Exact Byte Changes

### Patch 1

- File offset `0x001B7CCB`
- VA `0x005B7CCB`

```text
Original: 8B 4E 60 85 C9 74
Patched : E9 10 2F 16 00 90
```

### Patch 2

- File offset `0x001B80D2`
- VA `0x005B80D2`

```text
Original: 8A 45 18 84 C0 75 32
Patched : E9 49 2B 16 00 90 90
```

### Patch 3

- File offset `0x001B7916`
- VA `0x005B7916`

```text
Original: 8A 45 18 84 C0 74 07 B8 01 00 00 00 EB 05
Patched : E9 1C 33 16 00 90 90 90 90 90 90 90 90 90
```

### Patch 4

- File offset `0x0031ABE0`
- VA `0x0071ABE0`

```text
Original: 78 bytes of 00
Patched : 8B 4E 60 85 C9 75 34 8B 4E 54 85 C9 74 23 8D 44
          24 10 50 51 8B 01 FF 50 20 85 C0 7C 14 8B 54 24
          10 8B 7C 24 14 8B 46 40 8B 76 44 29 C2 19 F7 7C
          05 E9 E4 D0 E9 FF E9 EA D0 E9 FF E9 B2 D0 E9 FF
          83 7D 60 00 74 0C 8A 45 18 84 C0 75 05 E9 A7 D4
          E9 FF E9 D4 D4 E9 FF 83 7D 60 00 74 07 8A 45 18
          84 C0 74 0A B8 01 00 00 00 E9 DB CC E9 FF B8 88
          13 00 00 E9 D1 CC E9 FF
```

### Patch 5

- File offset `0x00198FA5`
- VA `0x00598FA5`

```text
Original: A9 FF 00 00 00 75 05 E8 2F F8 FF FF
Patched : E9 AE 1C 18 00 90 90 90 90 90 90 90
```

### Patch 6

- File offset `0x0031AC58`
- VA `0x0071AC58`

```text
Original: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
          00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
Patched : A9 FF 00 00 00 75 14 8B 0D 80 79 C9 00 85 C9 74
          05 80 39 00 75 05 E8 6D DB E7 FF E9 39 E3 E7 FF
```

## Technical Summary

The fixed logic is effectively:

```c
if (speech_object_has_no_sample) {
    current = stream->GetTime();
    eof = (current >= raw_duration);
    do_not_apply_duration_scale_8_over_6();
    post_eof_delay_ms = 1;
}

if (throne_script_finished) {
    if (speech_object_exists && speech_object_is_still_active) {
        keep_waiting;
    } else {
        original_cleanup();
    }
}
```

## Notes

- This is a permanent EXE patch, not a wrapper-based workaround.
- The patch was built specifically to stay small and targeted to the throne-room speech bug.
- If the patcher reports unsupported bytes, restore a clean `ShogunM.exe` first and then patch again.
