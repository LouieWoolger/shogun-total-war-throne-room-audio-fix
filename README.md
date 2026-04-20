# Shogun: Total War Gold - Throne Room Audio Fix

Patches `ShogunM.exe` directly to fix the throne-room speech cut-off bug on modern systems. Advisor, emissary, and priest speech lines play to the end instead of cutting off mid-sentence.

---

## What it fixes

On modern Windows, throne-room speech in Shogun: Total War Gold is cut off before the line finishes. This happens because of two bugs in the executable:

1. Audio-only stream objects report end-of-stream too early.
2. The throne script can destroy the speech object before playback has actually finished.

This tool patches both bugs in place.

---

## What it does not do

- It does not replace or modify any game audio files.
- It does not install a `dsound.dll` proxy or any runtime wrapper.
- It does not touch anything outside `ShogunM.exe`.
- It does not support EXE builds other than the ones listed under [Supported targets](#supported-targets).

If you have a `dsound.dll` or generated `.mp3.wav` files from an older workaround, remove them before testing.

---

## Requirements

- Windows
- Python 3

---

## Quick start

Run from a terminal in the folder containing the script:

```powershell
python .\shogun_throne_audio_fix.py "F:\Games\Shogun Total War Gold"
```

The script will back up `ShogunM.exe` as `ShogunM.exe.bak` before making any changes, then apply the patch and print the resulting SHA-256 hash.

---

## Usage

You can pass either the game folder or the EXE directly:

```powershell
# Patch using the game folder
python .\shogun_throne_audio_fix.py "F:\Games\Shogun Total War Gold"

# Or point at the EXE directly
python .\shogun_throne_audio_fix.py "F:\Games\Shogun Total War Gold\ShogunM.exe"
```

Check patch status without making changes:

```powershell
python .\shogun_throne_audio_fix.py --verify "F:\Games\Shogun Total War Gold"
```

Restore from backup:

```powershell
python .\shogun_throne_audio_fix.py --restore "F:\Games\Shogun Total War Gold"
```

`--verify` and `--restore` cannot be used together.

---

## Backup and restore

Before patching, the script creates:

```
ShogunM.exe.bak
```

in the same folder as the EXE. If a backup already exists, the script notes it and does not overwrite it.

To roll back:

- Run `--restore`, or
- Copy `ShogunM.exe.bak` back over `ShogunM.exe` manually.

---

## Verifying the fix in-game

1. Remove any older workaround files if present (`dsound.dll`, any `.mp3.wav` files).
2. Launch the patched `ShogunM.exe`.
3. Go to the throne room.
4. Click the advisor, emissary, or priest.
5. The speech line should now play through to the end.

---

## Supported targets

The patcher is strict. It checks the bytes at each patch location before writing anything. If the bytes do not match what is expected, it refuses to patch rather than writing over an unknown state.

The patch can be applied to:

- A clean original GOG or Steam `ShogunM.exe`
- A `ShogunM.exe` that already has my unit-cost patch applied

It cannot be applied to an EXE that has been modified in any other way. If the script reports unsupported bytes, restore a clean `ShogunM.exe` first and run the patcher again.

Known SHA-256 values for a correctly patched EXE:

```
11356636154934CC2FF2ED26B46FD82155C05EB52873FE6763F7FD22B1344D32  original GOG/Steam + audio fix
141C971763DC50AC2D5DD131E7FECAE87914C96FDB87B4EF25820E3B7A8C89DC  cost-fix-patched + audio fix
```

---

## Notes

- The patch offsets do not overlap with the unit-cost patch, so both can be applied independently in either order.
- If the script reports `status=already_patched`, no changes are made.
- The script writes directly to the open file handle and flushes before closing, so a partial write resulting from an interruption is unlikely, but the backup is there if needed.

---

## Technical details

### Root causes

**Bug 1 - early end-of-stream.** For audio-only `AMStream` objects (no video, no sample), the code was returning EOF immediately rather than checking the stream clock against the actual audio duration. This caused the speech to be considered finished before it was.

**Bug 2 - premature script cleanup.** Even after fixing the EOF check, the throne script object could still destroy the live speech object before playback finished. The script cleanup path lacked any check for whether the speech object was still active.

### What the patch does

- For the no-video/no-sample speech path: uses stream time to determine EOF rather than returning it immediately, and removes the incorrect `*8/6` duration scaling applied to that path.
- Removes the broken 5000 ms post-EOF linger on that path.
- Delays throne script cleanup until the active speech object reports itself as inactive.

The fixed logic is effectively:

```c
if (speech_object_has_no_sample) {
    current = stream->GetTime();
    eof = (current >= raw_duration);
    // no *8/6 scaling
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

### Patch locations

| # | File offset | VA | Description |
|---|---|---|---|
| 1 | `0x001B7CCB` | `0x005B7CCB` | EOF check entry to code cave |
| 2 | `0x001B80D2` | `0x005B80D2` | Duration scaling gate to code cave |
| 3 | `0x001B7916` | `0x005B7916` | Post-EOF delay selection to code cave |
| 4 | `0x0031ABE0` | `0x0071ABE0` | Stream timing code cave (120 bytes) |
| 5 | `0x00198FA5` | `0x00598FA5` | Script cleanup gate to code cave |
| 6 | `0x0031AC58` | `0x0071AC58` | Cleanup guard code cave (32 bytes) |
