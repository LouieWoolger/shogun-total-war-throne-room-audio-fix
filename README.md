# Shogun: Total War Gold - Throne Room Audio Fix (dsound workaround) v1.0.0

This release installs a proxy `dsound.dll` and generates `.mp3.wav` sidecar files so throne-room speech can be replayed externally instead of being cut off by the game.

## What It Does

- converts throne-room voice `*.mp3` files into `*.mp3.wav` sidecars
- installs a proxy `dsound.dll` in the game folder
- intercepts throne-room voice playback
- replays the matching WAV externally so lines can finish naturally
- stops external playback on scene changes, new quotes, and throne-room exit actions

## What It Creates

In the game folder, the script creates or uses:

- `dsound.dll`
- `dsound.bak`
- generated `*.mp3.wav` files

## Requirements

- Windows
- Python 3
- `ffmpeg` available on `PATH`
- MinGW-style `gcc` available on `PATH`

The script looks for:

- `ffmpeg` or `ffmpeg.exe`
- `i686-w64-mingw32-gcc`, `gcc`, or `cc`

## Usage

Install the workaround:

```powershell
python .\shogun_audio_fix.py "F:\Games\Total War Shogun 1 Gold"
```

Restore the original state:

```powershell
python .\shogun_audio_fix.py "F:\Games\Total War Shogun 1 Gold" --restore
```

## How Restore Works

Restore will:

- remove the proxy `dsound.dll`
- restore the original `dsound.dll` from `dsound.bak` if one was backed up
- remove generated `.mp3.wav` files

## Notes

- This is a workaround release, not a root-cause executable patch.
- It uses a proxy DLL and generated WAV sidecars rather than editing the game executable.
