#!/usr/bin/env python3
r"""
Shogun: Total War - Throne Room Audio Fix  (v1)
===================================================
Fixes:
1. Response clips play immediately (no 3500ms prime delay)
2. Scene exit: stops on music WAV file opens AND music buffer creation
3. Accept/Decline: stops on new MP3 file open
4. Advisor Done fallback: cancels advisor on throne-room exit click, including before speech starts

Usage:
    python shogun_audio_fix.py "F:\Games\Total War Shogun 1 Gold"
    python shogun_audio_fix.py "F:\Games\Total War Shogun 1 Gold" --restore
    python shogun_audio_fix.py "F:\Games\Total War Shogun 1 Gold" --debug-log
"""

import argparse, os, shutil, subprocess, sys, tempfile
from pathlib import Path

DSOUND_C = r"""
#define WIN32_LEAN_AND_MEAN
#define ENABLE_LOGGING __ENABLE_LOGGING__
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <mmsystem.h>

typedef struct IDirectSound IDirectSound;
typedef struct IDirectSoundBuffer IDirectSoundBuffer;

#pragma pack(push, 1)
typedef struct {
    WORD wFormatTag; WORD nChannels;
    DWORD nSamplesPerSec; DWORD nAvgBytesPerSec;
    WORD nBlockAlign; WORD wBitsPerSample; WORD cbSize;
} WFXMIN;
#pragma pack(pop)

typedef struct {
    DWORD dwSize; DWORD dwFlags; DWORD dwBufferBytes;
    DWORD dwReserved; WFXMIN *lpwfxFormat;
} DSBDMIN;

typedef struct {
    HRESULT (__stdcall *QueryInterface)(IDirectSoundBuffer*, const IID*, void**);
    ULONG   (__stdcall *AddRef)(IDirectSoundBuffer*);
    ULONG   (__stdcall *Release)(IDirectSoundBuffer*);
    HRESULT (__stdcall *GetCaps)(IDirectSoundBuffer*, void*);
    HRESULT (__stdcall *GetCurrentPosition)(IDirectSoundBuffer*, DWORD*, DWORD*);
    HRESULT (__stdcall *GetFormat)(IDirectSoundBuffer*, void*, DWORD, DWORD*);
    HRESULT (__stdcall *GetVolume)(IDirectSoundBuffer*, LONG*);
    HRESULT (__stdcall *GetPan)(IDirectSoundBuffer*, LONG*);
    HRESULT (__stdcall *GetFrequency)(IDirectSoundBuffer*, DWORD*);
    HRESULT (__stdcall *GetStatus)(IDirectSoundBuffer*, DWORD*);
    HRESULT (__stdcall *Initialize)(IDirectSoundBuffer*, IDirectSound*, const DSBDMIN*);
    HRESULT (__stdcall *Lock)(IDirectSoundBuffer*, DWORD, DWORD, void**, DWORD*, void**, DWORD*, DWORD);
    HRESULT (__stdcall *Play)(IDirectSoundBuffer*, DWORD, DWORD, DWORD);
    HRESULT (__stdcall *SetCurrentPosition)(IDirectSoundBuffer*, DWORD);
    HRESULT (__stdcall *SetFormat)(IDirectSoundBuffer*, const void*);
    HRESULT (__stdcall *SetVolume)(IDirectSoundBuffer*, LONG);
    HRESULT (__stdcall *SetPan)(IDirectSoundBuffer*, LONG);
    HRESULT (__stdcall *SetFrequency)(IDirectSoundBuffer*, DWORD);
    HRESULT (__stdcall *Stop)(IDirectSoundBuffer*);
    HRESULT (__stdcall *Unlock)(IDirectSoundBuffer*, void*, DWORD, void*, DWORD);
    HRESULT (__stdcall *Restore)(IDirectSoundBuffer*);
} DSBVtbl;
struct IDirectSoundBuffer { DSBVtbl *lpVtbl; };

typedef struct {
    HRESULT (__stdcall *QueryInterface)(IDirectSound*, const IID*, void**);
    ULONG   (__stdcall *AddRef)(IDirectSound*);
    ULONG   (__stdcall *Release)(IDirectSound*);
    HRESULT (__stdcall *CreateSoundBuffer)(IDirectSound*, const DSBDMIN*, IDirectSoundBuffer**, void*);
    HRESULT (__stdcall *GetCaps)(IDirectSound*, void*);
    HRESULT (__stdcall *DuplicateSoundBuffer)(IDirectSound*, IDirectSoundBuffer*, IDirectSoundBuffer**);
    HRESULT (__stdcall *SetCooperativeLevel)(IDirectSound*, HWND, DWORD);
    HRESULT (__stdcall *Compact)(IDirectSound*);
    HRESULT (__stdcall *GetSpeakerConfig)(IDirectSound*, DWORD*);
    HRESULT (__stdcall *SetSpeakerConfig)(IDirectSound*, DWORD);
    HRESULT (__stdcall *Initialize)(IDirectSound*, const GUID*);
} DSVtbl;
struct IDirectSound { DSVtbl *lpVtbl; };

typedef HRESULT (WINAPI *DSCreate_t)(const GUID*, IDirectSound**, void*);
static HMODULE hReal = NULL;
static DSCreate_t real_DSCreate = NULL;
static FARPROC real_DSEnumA, real_DSEnumW;
static FARPROC real_DSCapCreate, real_DSCapEnumA, real_DSCapEnumW;
static FARPROC real_DllCanUnloadNow, real_DllGetClassObject;
static FARPROC real_DSCreate8, real_DSFullDuplexCreate;
typedef LRESULT (WINAPI *DispatchMessageA_t)(const MSG*);
typedef LRESULT (WINAPI *DispatchMessageW_t)(const MSG*);
static DispatchMessageA_t orig_DispatchMessageA = NULL;
static DispatchMessageW_t orig_DispatchMessageW = NULL;

#if ENABLE_LOGGING
static FILE *logFile = NULL;
static DWORD startTick = 0;
static CRITICAL_SECTION logCS;
#endif
static int nextBufId = 1;
static char gameDir[MAX_PATH] = {0};

#define DSBCAPS_GCP2 0x80000
#define MAX_VOICE_STREAM_SIZE 65536
#define MUSIC_BUFFER_MIN_SIZE 750000
#define BIG_BUFFER_LOG_MIN_SIZE 400000
#if ENABLE_LOGGING
static void L(const char *fmt, ...) {
    if (!logFile) return;
    EnterCriticalSection(&logCS);
    fprintf(logFile, "[%7lu ms] ", GetTickCount() - startTick);
    va_list a; va_start(a, fmt); vfprintf(logFile, fmt, a); va_end(a);
    fprintf(logFile, "\n"); fflush(logFile);
    LeaveCriticalSection(&logCS);
}
#else
#define L(...) ((void)0)
#endif

/* Case-insensitive substring search */
static int contains_ci(const char *haystack, const char *needle) {
    int nlen = lstrlenA(needle);
    int hlen = lstrlenA(haystack);
    int i, j;
    for (i = 0; i <= hlen - nlen; i++) {
        for (j = 0; j < nlen; j++) {
            char h = haystack[i+j], n = needle[j];
            if (h >= 'A' && h <= 'Z') h += 32;
            if (n >= 'A' && n <= 'Z') n += 32;
            if (h != n) break;
        }
        if (j == nlen) return 1;
    }
    return 0;
}

/* ---- waveOut playback ---- */
typedef MMRESULT (WINAPI *waveOutOpen_t)(LPHWAVEOUT, UINT, LPCWAVEFORMATEX, DWORD_PTR, DWORD_PTR, DWORD);
typedef MMRESULT (WINAPI *waveOutPrepareHeader_t)(HWAVEOUT, LPWAVEHDR, UINT);
typedef MMRESULT (WINAPI *waveOutWrite_t)(HWAVEOUT, LPWAVEHDR, UINT);
typedef MMRESULT (WINAPI *waveOutUnprepareHeader_t)(HWAVEOUT, LPWAVEHDR, UINT);
typedef MMRESULT (WINAPI *waveOutReset_t)(HWAVEOUT);
typedef MMRESULT (WINAPI *waveOutClose_t)(HWAVEOUT);

static HMODULE hWinmm = NULL;
static waveOutOpen_t pWaveOutOpen = NULL;
static waveOutPrepareHeader_t pWaveOutPrepareHeader = NULL;
static waveOutWrite_t pWaveOutWrite = NULL;
static waveOutUnprepareHeader_t pWaveOutUnprepareHeader = NULL;
static waveOutReset_t pWaveOutReset = NULL;
static waveOutClose_t pWaveOutClose = NULL;
static int psInited = 0;

static char primedFile[MAX_PATH] = {0};
static DWORD primedTick = 0;
static volatile LONG primedGen = 0;
static volatile LONG playGen = 0;
static char playingFile[MAX_PATH] = {0};
static DWORD playingTick = 0;
static HWAVEOUT hWaveOut = NULL;
static WAVEHDR waveHdr;
static BYTE *waveData = NULL;
static CRITICAL_SECTION playCS;

#define PRIME_MIN_MS 500
#define AUTOFIRE_MS 3500

static DWORD rd_le32(const BYTE *p) {
    return ((DWORD)p[0]) | ((DWORD)p[1] << 8) | ((DWORD)p[2] << 16) | ((DWORD)p[3] << 24);
}

typedef struct {
    LONG gen;
    DWORD durationMs;
} ClearPlayParam;

static void WaveCleanupLocked(void) {
    MMRESULT mm;
    int i;
    if (hWaveOut) {
        if (pWaveOutReset) {
            mm = pWaveOutReset(hWaveOut);
            L("PS: waveOutReset -> %lu", (DWORD)mm);
        }
        if ((waveHdr.dwFlags & WHDR_PREPARED) && pWaveOutUnprepareHeader) {
            mm = MMSYSERR_NOERROR;
            for (i = 0; i < 8; i++) {
                mm = pWaveOutUnprepareHeader(hWaveOut, &waveHdr, sizeof(waveHdr));
                if (mm != WAVERR_STILLPLAYING) break;
                Sleep(10);
            }
            L("PS: waveOutUnprepareHeader -> %lu", (DWORD)mm);
        }
        if (pWaveOutClose) {
            mm = MMSYSERR_NOERROR;
            for (i = 0; i < 8; i++) {
                mm = pWaveOutClose(hWaveOut);
                if (mm != WAVERR_STILLPLAYING) break;
                Sleep(10);
            }
            L("PS: waveOutClose -> %lu", (DWORD)mm);
        }
        hWaveOut = NULL;
    }
    ZeroMemory(&waveHdr, sizeof(waveHdr));
    if (waveData) {
        HeapFree(GetProcessHeap(), 0, waveData);
        waveData = NULL;
    }
    playingFile[0] = '\0';
    playingTick = 0;
}

/* Load a PCM WAV sidecar so we can own playback and stop it immediately
   on scene transitions, instead of relying on PlaySound's process-global state. */
static int LoadWavFile(const char *wavPath, WAVEFORMATEX *fmt, BYTE **dataOut,
                       DWORD *dataSizeOut, DWORD *durationMsOut) {
    HANDLE h = CreateFileA(wavPath, GENERIC_READ, FILE_SHARE_READ, NULL,
                           OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    BYTE hdr[64];
    DWORD got = 0, dataSize = 0;
    DWORD avgBytes = 0;
    BYTE *data = NULL;
    if (h == INVALID_HANDLE_VALUE) return 0;
    ZeroMemory(fmt, sizeof(*fmt));
    if (!ReadFile(h, hdr, 12, &got, NULL) || got < 12 ||
        memcmp(hdr, "RIFF", 4) != 0 || memcmp(hdr + 8, "WAVE", 4) != 0) {
        CloseHandle(h);
        return 0;
    }
    while (ReadFile(h, hdr, 8, &got, NULL) && got == 8) {
        DWORD chunkSize = rd_le32(hdr + 4);
        if (memcmp(hdr, "fmt ", 4) == 0) {
            DWORD need = chunkSize < sizeof(hdr) ? chunkSize : sizeof(hdr);
            if (!ReadFile(h, hdr, need, &got, NULL) || got < need) break;
            if (chunkSize > need)
                SetFilePointer(h, chunkSize - need, NULL, FILE_CURRENT);
            if (need >= 16) {
                memcpy(fmt, hdr, need < sizeof(*fmt) ? need : sizeof(*fmt));
                avgBytes = fmt->nAvgBytesPerSec;
            }
        } else if (memcmp(hdr, "data", 4) == 0) {
            dataSize = chunkSize;
            data = (BYTE*)HeapAlloc(GetProcessHeap(), 0, dataSize);
            if (!data) break;
            if (!ReadFile(h, data, dataSize, &got, NULL) || got < dataSize) {
                HeapFree(GetProcessHeap(), 0, data);
                data = NULL;
                break;
            }
            break;
        } else {
            SetFilePointer(h, chunkSize, NULL, FILE_CURRENT);
        }
        if (chunkSize & 1)
            SetFilePointer(h, 1, NULL, FILE_CURRENT);
    }
    CloseHandle(h);
    if (!avgBytes || !dataSize || !data) {
        if (data) HeapFree(GetProcessHeap(), 0, data);
        return 0;
    }
    *dataOut = data;
    *dataSizeOut = dataSize;
    *durationMsOut = (DWORD)(((unsigned long long)dataSize * 1000ULL + avgBytes - 1) / avgBytes);
    return 1;
}

static DWORD WINAPI ClearPlayThread(LPVOID param) {
    ClearPlayParam *cp = (ClearPlayParam*)param;
    DWORD waitMs = cp->durationMs;
    if (waitMs < 500) waitMs = 500;
    if (waitMs > 300000) waitMs = 300000;
    Sleep(waitMs + 750);
    EnterCriticalSection(&playCS);
    if (InterlockedCompareExchange(&playGen, cp->gen, cp->gen) == cp->gen)
        WaveCleanupLocked();
    LeaveCriticalSection(&playCS);
    HeapFree(GetProcessHeap(), 0, cp);
    return 0;
}

static void PS_Init(void) {
    if (psInited) return;
    hWinmm = LoadLibraryA("winmm.dll");
    if (hWinmm) {
        pWaveOutOpen = (waveOutOpen_t)GetProcAddress(hWinmm, "waveOutOpen");
        pWaveOutPrepareHeader = (waveOutPrepareHeader_t)GetProcAddress(hWinmm, "waveOutPrepareHeader");
        pWaveOutWrite = (waveOutWrite_t)GetProcAddress(hWinmm, "waveOutWrite");
        pWaveOutUnprepareHeader = (waveOutUnprepareHeader_t)GetProcAddress(hWinmm, "waveOutUnprepareHeader");
        pWaveOutReset = (waveOutReset_t)GetProcAddress(hWinmm, "waveOutReset");
        pWaveOutClose = (waveOutClose_t)GetProcAddress(hWinmm, "waveOutClose");
    }
    psInited = 1;
}

static void PS_StopNow(void) {
    LONG gen = InterlockedIncrement(&playGen);
    EnterCriticalSection(&playCS);
    WaveCleanupLocked();
    LeaveCriticalSection(&playCS);
    L("PS: STOP (%ld)", gen);
}

static void PS_DoPlay(const char *wavPath) {
    PS_Init();
    if (!pWaveOutOpen || !pWaveOutPrepareHeader || !pWaveOutWrite || !pWaveOutClose) {
        L("PS: waveOut unavailable");
        return;
    }
    DWORD attr = GetFileAttributesA(wavPath);
    if (attr == INVALID_FILE_ATTRIBUTES) {
        L("PS: WAV not found: %s", wavPath);
        return;
    }
    WAVEFORMATEX fmt;
    DWORD durationMs = 0, dataSize = 0;
    BYTE *data = NULL;
    if (!LoadWavFile(wavPath, &fmt, &data, &dataSize, &durationMs)) {
        L("PS: WAV load failed: %s", wavPath);
        return;
    }

    LONG gen = InterlockedIncrement(&playGen);
    EnterCriticalSection(&playCS);
    WaveCleanupLocked();
    waveData = data;
    ZeroMemory(&waveHdr, sizeof(waveHdr));
    MMRESULT mm = pWaveOutOpen(&hWaveOut, WAVE_MAPPER, &fmt, 0, 0, CALLBACK_NULL);
    if (mm != MMSYSERR_NOERROR) {
        WaveCleanupLocked();
        LeaveCriticalSection(&playCS);
        L("PS: waveOutOpen failed (%lu) %s", (DWORD)mm, wavPath);
        return;
    }
    waveHdr.lpData = (LPSTR)waveData;
    waveHdr.dwBufferLength = dataSize;
    mm = pWaveOutPrepareHeader(hWaveOut, &waveHdr, sizeof(waveHdr));
    if (mm != MMSYSERR_NOERROR) {
        WaveCleanupLocked();
        LeaveCriticalSection(&playCS);
        L("PS: waveOutPrepareHeader failed (%lu) %s", (DWORD)mm, wavPath);
        return;
    }
    mm = pWaveOutWrite(hWaveOut, &waveHdr, sizeof(waveHdr));
    if (mm != MMSYSERR_NOERROR) {
        WaveCleanupLocked();
        LeaveCriticalSection(&playCS);
        L("PS: waveOutWrite failed (%lu) %s", (DWORD)mm, wavPath);
        return;
    }
    lstrcpynA(playingFile, wavPath, MAX_PATH);
    playingTick = GetTickCount();
    LeaveCriticalSection(&playCS);

    ClearPlayParam *cp = (ClearPlayParam*)HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, sizeof(ClearPlayParam));
    if (cp) {
        cp->gen = gen;
        cp->durationMs = durationMs ? durationMs : 15000;
        HANDLE t = CreateThread(NULL, 0, ClearPlayThread, cp, 0, NULL);
        if (t) CloseHandle(t);
        else HeapFree(GetProcessHeap(), 0, cp);
    }
    L("PS: >>> PLAYING <<< %s (%lums)", wavPath, durationMs ? durationMs : 15000);
}

static DWORD WINAPI AutoFireThread(LPVOID param) {
    LONG myGen = (LONG)(LONG_PTR)param;
    Sleep(AUTOFIRE_MS);
    if (InterlockedCompareExchange(&primedGen, myGen, myGen) == myGen) {
        if (primedFile[0]) {
            L("PS: AUTO-FIRE (timeout %dms)", AUTOFIRE_MS);
            PS_DoPlay(primedFile);
            primedFile[0] = '\0';
        }
    }
    return 0;
}

static void PS_TryPlay(const char *mp3Path) {
    PS_Init();
    if (!pWaveOutOpen) return;

    char wavPath[MAX_PATH];
    lstrcpynA(wavPath, mp3Path, MAX_PATH - 5);
    lstrcatA(wavPath, ".wav");

    DWORD now = GetTickCount();

    /* Already playing this file? Skip duplicate trigger groups. */
    if (playingFile[0] && lstrcmpiA(playingFile, wavPath) == 0) {
        L("PS: already playing, skip");
        return;
    }

    /* Same file as primed? Check timing -> FIRE */
    if (primedFile[0] && lstrcmpiA(primedFile, wavPath) == 0) {
        DWORD elapsed = now - primedTick;
        if (elapsed >= PRIME_MIN_MS) {
            L("PS: FIRE after %lums prime", elapsed);
            PS_DoPlay(wavPath);
            primedFile[0] = '\0';
            return;
        } else {
            L("PS: primed %lums ago, waiting", elapsed);
            return;
        }
    }

    /* Response clips (Accept/Reject/Rejected/Accepted) play immediately.
       They have no bow animation, so no need for prime/fire delay. */
    if (contains_ci(mp3Path, "\\Response\\")) {
        L("PS: IMMEDIATE (response clip)");
        PS_DoPlay(wavPath);
        return;
    }

    /* Normal clip -> PRIME + start auto-fire timer */
    lstrcpynA(primedFile, wavPath, MAX_PATH);
    primedTick = now;
    LONG gen = InterlockedIncrement(&primedGen);
    L("PS: PRIMED %s", wavPath);

    HANDLE t = CreateThread(NULL, 0, AutoFireThread, (LPVOID)(LONG_PTR)gen, 0, NULL);
    if (t) CloseHandle(t);
}

/* ---- CreateFileA IAT Hook ---- */
typedef HANDLE (WINAPI *CreateFileA_t)(LPCSTR,DWORD,DWORD,LPSECURITY_ATTRIBUTES,DWORD,DWORD,HANDLE);
static CreateFileA_t orig_CreateFileA = NULL;
static char lastMp3Path[MAX_PATH] = {0};
static CRITICAL_SECTION pathCS;

static HANDLE WINAPI hook_CreateFileA(LPCSTR path, DWORD a, DWORD sh,
    LPSECURITY_ATTRIBUTES sa, DWORD d, DWORD fl, HANDLE t)
{
    if (path) {
        int len = lstrlenA(path);

        /* Detect MP3 files -> track path + stop on new file */
        if (len > 4 && lstrcmpiA(path+len-4, ".mp3") == 0) {
            EnterCriticalSection(&pathCS);

            char fullPath[MAX_PATH];
            if (path[0]!='\\' && (len<2||path[1]!=':')) {
                lstrcpynA(fullPath, gameDir, MAX_PATH);
                lstrcatA(fullPath, path);
            } else {
                lstrcpynA(fullPath, path, MAX_PATH);
            }

            if (lastMp3Path[0] && lstrcmpiA(lastMp3Path, fullPath) != 0) {
                L("New MP3 -> stopping previous audio");
                PS_StopNow();
                primedFile[0] = '\0';
                InterlockedIncrement(&primedGen);
            }

            lstrcpynA(lastMp3Path, fullPath, MAX_PATH);
            L("CreateFileA: MP3 -> %s", lastMp3Path);
            LeaveCriticalSection(&pathCS);
        }
    }
    return orig_CreateFileA(path, a, sh, sa, d, fl, t);
}

/* ---- mmioOpenA hook for scene exit detection ---- */
/* During throne room voice playback, the game makes ZERO mmioOpenA calls.
   All voice audio goes through DirectSound/CreateFileA (MP3s).
   Therefore ANY mmioOpenA call while voice is playing = scene transition. */
typedef void* HMMIO_T;
typedef struct { char dummy[64]; } MMIOINFO_T;
typedef HMMIO_T (WINAPI *mmioOpenA_t)(LPSTR, MMIOINFO_T*, DWORD);
static mmioOpenA_t orig_mmioOpenA = NULL;

static HMMIO_T WINAPI hook_mmioOpenA(LPSTR path, MMIOINFO_T *info, DWORD flags) {
    if (path && (playingFile[0] || primedFile[0])) {
        L("mmioOpenA(%s) -> scene exit, stopping voice", path);
        PS_StopNow();
        primedFile[0] = '\0';
        InterlockedIncrement(&primedGen);
    }
    return orig_mmioOpenA(path, info, flags);
}

static int AdvisorAudioActive(void) {
    return contains_ci(playingFile, "\\Advisor\\") || contains_ci(primedFile, "\\Advisor\\");
}

static int IsLikelyThroneExitClick(const MSG *msg) {
    int x, y;
    if (!msg || msg->message != WM_LBUTTONDOWN) return 0;
    x = (short)LOWORD(msg->lParam);
    y = (short)HIWORD(msg->lParam);
    return (y >= 520 && x >= 320 && x <= 640);
}

static void StopAdvisorOnUiAction(const MSG *msg, const char *tag) {
    if (!msg || !AdvisorAudioActive()) return;
    if (IsLikelyThroneExitClick(msg)) {
        int x = (short)LOWORD(msg->lParam);
        int y = (short)HIWORD(msg->lParam);
        L("%s: throne exit click x=%d y=%d -> stopping advisor", tag, x, y);
        PS_StopNow();
        primedFile[0] = '\0';
        InterlockedIncrement(&primedGen);
    }
}

static LRESULT WINAPI hook_DispatchMessageA(const MSG *msg) {
    StopAdvisorOnUiAction(msg, "DispatchMessageA");
    return orig_DispatchMessageA ? orig_DispatchMessageA(msg) : 0;
}

static LRESULT WINAPI hook_DispatchMessageW(const MSG *msg) {
    StopAdvisorOnUiAction(msg, "DispatchMessageW");
    return orig_DispatchMessageW ? orig_DispatchMessageW(msg) : 0;
}

static void HookIAT(void) {
    HMODULE hExe = GetModuleHandleA(NULL);
    PIMAGE_DOS_HEADER dos = (PIMAGE_DOS_HEADER)hExe;
    if (dos->e_magic != IMAGE_DOS_SIGNATURE) return;
    PIMAGE_NT_HEADERS nt = (PIMAGE_NT_HEADERS)((BYTE*)hExe + dos->e_lfanew);
    if (nt->Signature != IMAGE_NT_SIGNATURE) return;
    DWORD impRVA = nt->OptionalHeader.DataDirectory[1].VirtualAddress;
    if (!impRVA) return;
    PIMAGE_IMPORT_DESCRIPTOR imp = (PIMAGE_IMPORT_DESCRIPTOR)((BYTE*)hExe + impRVA);
    int hookedCFA = 0, hookedMmio = 0, hookedDispA = 0, hookedDispW = 0;
    for (; imp->Name; imp++) {
        char *dll = (char*)((BYTE*)hExe + imp->Name);
        int isKernel32 = (lstrcmpiA(dll, "kernel32.dll") == 0);
        int isWinmm = (lstrcmpiA(dll, "winmm.dll") == 0);
        int isUser32 = (lstrcmpiA(dll, "user32.dll") == 0);
        if (!isKernel32 && !isWinmm && !isUser32) continue;

        PIMAGE_THUNK_DATA orig = (PIMAGE_THUNK_DATA)((BYTE*)hExe + imp->OriginalFirstThunk);
        PIMAGE_THUNK_DATA thunk = (PIMAGE_THUNK_DATA)((BYTE*)hExe + imp->FirstThunk);
        for (; orig->u1.AddressOfData; orig++, thunk++) {
            if (orig->u1.Ordinal & IMAGE_ORDINAL_FLAG) continue;
            PIMAGE_IMPORT_BY_NAME ibn = (PIMAGE_IMPORT_BY_NAME)((BYTE*)hExe + orig->u1.AddressOfData);
            char *fname = (char*)ibn->Name;

            if (isKernel32 && !hookedCFA && lstrcmpA(fname, "CreateFileA") == 0) {
                DWORD old;
                VirtualProtect(&thunk->u1.Function, sizeof(void*), PAGE_READWRITE, &old);
                orig_CreateFileA = (CreateFileA_t)thunk->u1.Function;
                thunk->u1.Function = (DWORD_PTR)hook_CreateFileA;
                VirtualProtect(&thunk->u1.Function, sizeof(void*), old, &old);
                L("IAT: CreateFileA hooked");
                hookedCFA = 1;
            }
            if (isWinmm && !hookedMmio && lstrcmpA(fname, "mmioOpenA") == 0) {
                DWORD old;
                VirtualProtect(&thunk->u1.Function, sizeof(void*), PAGE_READWRITE, &old);
                orig_mmioOpenA = (mmioOpenA_t)thunk->u1.Function;
                thunk->u1.Function = (DWORD_PTR)hook_mmioOpenA;
                VirtualProtect(&thunk->u1.Function, sizeof(void*), old, &old);
                L("IAT: mmioOpenA hooked");
                hookedMmio = 1;
            }
            if (isUser32 && !hookedDispA && lstrcmpA(fname, "DispatchMessageA") == 0) {
                DWORD old;
                VirtualProtect(&thunk->u1.Function, sizeof(void*), PAGE_READWRITE, &old);
                orig_DispatchMessageA = (DispatchMessageA_t)thunk->u1.Function;
                thunk->u1.Function = (DWORD_PTR)hook_DispatchMessageA;
                VirtualProtect(&thunk->u1.Function, sizeof(void*), old, &old);
                L("IAT: DispatchMessageA hooked");
                hookedDispA = 1;
            }
            if (isUser32 && !hookedDispW && lstrcmpA(fname, "DispatchMessageW") == 0) {
                DWORD old;
                VirtualProtect(&thunk->u1.Function, sizeof(void*), PAGE_READWRITE, &old);
                orig_DispatchMessageW = (DispatchMessageW_t)thunk->u1.Function;
                thunk->u1.Function = (DWORD_PTR)hook_DispatchMessageW;
                VirtualProtect(&thunk->u1.Function, sizeof(void*), old, &old);
                L("IAT: DispatchMessageW hooked");
                hookedDispW = 1;
            }
        }
    }
    if (!hookedCFA)
        orig_CreateFileA = (CreateFileA_t)GetProcAddress(GetModuleHandleA("kernel32.dll"), "CreateFileA");
    if (!hookedMmio)
        L("IAT: mmioOpenA NOT found in IAT (scene exit via music buffer only)");
}

/* ---- Wrapped Buffers ---- */
typedef struct WrapDS WrapDS;
typedef struct {
    DSBVtbl *lpVtbl;
    IDirectSoundBuffer *real;
    LONG refCount;
    int id;
    DWORD bufSize, bufFlags;
    int isVoiceStream;
    char mp3Path[MAX_PATH];
} WrapBuf;
static DSBVtbl wbVtbl;

typedef struct WrapDS {
    DSVtbl *lpVtbl;
    IDirectSound *real;
    LONG refCount;
} WrapDS;
static DSVtbl wdsVtbl;

static HRESULT __stdcall WB_QI(IDirectSoundBuffer *p,const IID *i,void **o){WrapBuf *w=(WrapBuf*)p;return w->real->lpVtbl->QueryInterface(w->real,i,o);}
static ULONG __stdcall WB_AR(IDirectSoundBuffer *p){WrapBuf *w=(WrapBuf*)p;return InterlockedIncrement(&w->refCount);}
static ULONG __stdcall WB_Rl(IDirectSoundBuffer *p){
    WrapBuf *w=(WrapBuf*)p;
    LONG rc=InterlockedDecrement(&w->refCount);
    if(rc<=0){
        /* Large buffer release while voice playing = scene exit */
        if (playingFile[0] || primedFile[0]) {
            if (w->bufSize >= MUSIC_BUFFER_MIN_SIZE) {
                L("buf[%d] MUSIC RELEASE (size=%lu) -> scene exit, stopping voice", w->id, w->bufSize);
                PS_StopNow();
                primedFile[0] = '\0';
                InterlockedIncrement(&primedGen);
            } else if (w->bufSize >= BIG_BUFFER_LOG_MIN_SIZE) {
                L("buf[%d] BIG RELEASE (size=%lu)", w->id, w->bufSize);
            }
        }
        w->real->lpVtbl->Release(w->real);
        HeapFree(GetProcessHeap(),0,w);
    }
    return rc;
}
static HRESULT __stdcall WB_GC(IDirectSoundBuffer *p,void *c){WrapBuf *w=(WrapBuf*)p;return w->real->lpVtbl->GetCaps(w->real,c);}
static HRESULT __stdcall WB_GCP(IDirectSoundBuffer *p,DWORD *a,DWORD *b){WrapBuf *w=(WrapBuf*)p;return w->real->lpVtbl->GetCurrentPosition(w->real,a,b);}
static HRESULT __stdcall WB_GF(IDirectSoundBuffer *p,void *f,DWORD s,DWORD *x){WrapBuf *w=(WrapBuf*)p;return w->real->lpVtbl->GetFormat(w->real,f,s,x);}
static HRESULT __stdcall WB_GV(IDirectSoundBuffer *p,LONG *v){WrapBuf *w=(WrapBuf*)p;return w->real->lpVtbl->GetVolume(w->real,v);}
static HRESULT __stdcall WB_GPn(IDirectSoundBuffer *p,LONG *v){WrapBuf *w=(WrapBuf*)p;return w->real->lpVtbl->GetPan(w->real,v);}
static HRESULT __stdcall WB_GFr(IDirectSoundBuffer *p,DWORD *v){WrapBuf *w=(WrapBuf*)p;return w->real->lpVtbl->GetFrequency(w->real,v);}
static HRESULT __stdcall WB_GS(IDirectSoundBuffer *p,DWORD *s){WrapBuf *w=(WrapBuf*)p;return w->real->lpVtbl->GetStatus(w->real,s);}
static HRESULT __stdcall WB_In(IDirectSoundBuffer *p,IDirectSound *d,const DSBDMIN *x){WrapBuf *w=(WrapBuf*)p;return w->real->lpVtbl->Initialize(w->real,d,x);}
static HRESULT __stdcall WB_Lk(IDirectSoundBuffer *p,DWORD o,DWORD b,void **p1,DWORD *s1,void **p2,DWORD *s2,DWORD f){WrapBuf *w=(WrapBuf*)p;return w->real->lpVtbl->Lock(w->real,o,b,p1,s1,p2,s2,f);}

static HRESULT __stdcall WB_Play(IDirectSoundBuffer *p, DWORD r1, DWORD r2, DWORD flags) {
    WrapBuf *w = (WrapBuf*)p;
    if (w->isVoiceStream && w->mp3Path[0]) {
        PS_TryPlay(w->mp3Path);
        w->real->lpVtbl->SetVolume(w->real, -10000);
        return w->real->lpVtbl->Play(w->real, r1, r2, flags);
    }
    return w->real->lpVtbl->Play(w->real, r1, r2, flags);
}

static HRESULT __stdcall WB_SCP(IDirectSoundBuffer *p,DWORD pos){WrapBuf *w=(WrapBuf*)p;return w->real->lpVtbl->SetCurrentPosition(w->real,pos);}
static HRESULT __stdcall WB_SF(IDirectSoundBuffer *p,const void *f){WrapBuf *w=(WrapBuf*)p;return w->real->lpVtbl->SetFormat(w->real,f);}
static HRESULT __stdcall WB_SV(IDirectSoundBuffer *p,LONG v){WrapBuf *w=(WrapBuf*)p;return w->real->lpVtbl->SetVolume(w->real,v);}
static HRESULT __stdcall WB_SPn(IDirectSoundBuffer *p,LONG v){WrapBuf *w=(WrapBuf*)p;return w->real->lpVtbl->SetPan(w->real,v);}
static HRESULT __stdcall WB_SFr(IDirectSoundBuffer *p,DWORD v){WrapBuf *w=(WrapBuf*)p;return w->real->lpVtbl->SetFrequency(w->real,v);}
static HRESULT __stdcall WB_Stop(IDirectSoundBuffer *p) {
    WrapBuf *w = (WrapBuf*)p;
    /* Large music buffer stop = scene exit -> stop voice immediately */
    if (playingFile[0] || primedFile[0]) {
        if (w->bufSize >= MUSIC_BUFFER_MIN_SIZE) {
            L("buf[%d] MUSIC STOP (size=%lu) -> scene exit, stopping voice", w->id, w->bufSize);
            PS_StopNow();
            primedFile[0] = '\0';
            InterlockedIncrement(&primedGen);
        } else if (w->bufSize >= BIG_BUFFER_LOG_MIN_SIZE) {
            L("buf[%d] BIG STOP (size=%lu)", w->id, w->bufSize);
        }
    }
    /* Voice buffer stop: do NOT use delayed stop. It cuts off long clips.
       Audio stops via: natural end, CreateFileA (new clip), mmioOpenA,
       or music buffer stop/release (scene exit). */
    return w->real->lpVtbl->Stop(w->real);
}
static HRESULT __stdcall WB_Ul(IDirectSoundBuffer *p,void *p1,DWORD s1,void *p2,DWORD s2){WrapBuf *w=(WrapBuf*)p;return w->real->lpVtbl->Unlock(w->real,p1,s1,p2,s2);}
static HRESULT __stdcall WB_Rs(IDirectSoundBuffer *p){WrapBuf *w=(WrapBuf*)p;return w->real->lpVtbl->Restore(w->real);}

static DSBVtbl wbVtbl = {
    WB_QI,WB_AR,WB_Rl,WB_GC,WB_GCP,WB_GF,WB_GV,WB_GPn,WB_GFr,WB_GS,
    WB_In,WB_Lk,WB_Play,WB_SCP,WB_SF,WB_SV,WB_SPn,WB_SFr,WB_Stop,WB_Ul,WB_Rs
};

static HRESULT __stdcall DS_QI(IDirectSound *p,const IID *i,void **o){WrapDS *w=(WrapDS*)p;return w->real->lpVtbl->QueryInterface(w->real,i,o);}
static ULONG __stdcall DS_AR(IDirectSound *p){WrapDS *w=(WrapDS*)p;return InterlockedIncrement(&w->refCount);}
static ULONG __stdcall DS_Rl(IDirectSound *p){WrapDS *w=(WrapDS*)p;LONG rc=InterlockedDecrement(&w->refCount);if(rc<=0){w->real->lpVtbl->Release(w->real);HeapFree(GetProcessHeap(),0,w);}return rc;}

static HRESULT __stdcall DS_CSB(IDirectSound *p, const DSBDMIN *desc, IDirectSoundBuffer **ppBuf, void *unk) {
    WrapDS *wds=(WrapDS*)p;
    IDirectSoundBuffer *rb=NULL;
    HRESULT hr=wds->real->lpVtbl->CreateSoundBuffer(wds->real,desc,&rb,unk);
    if(hr==0&&rb&&ppBuf){
        DWORD sz=desc?desc->dwBufferBytes:0, fl=desc?desc->dwFlags:0;
        WrapBuf *wb=(WrapBuf*)HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,sizeof(WrapBuf));
        wb->lpVtbl=&wbVtbl;wb->real=rb;wb->refCount=1;wb->id=nextBufId++;wb->bufSize=sz;wb->bufFlags=fl;

        if(sz>0&&sz<=MAX_VOICE_STREAM_SIZE&&(fl&DSBCAPS_GCP2)){
            wb->isVoiceStream=1;
            EnterCriticalSection(&pathCS);
            lstrcpynA(wb->mp3Path,lastMp3Path,MAX_PATH);
            LeaveCriticalSection(&pathCS);
            L("buf[%d] VOICE (size=%lu) mp3=%s",wb->id,sz,wb->mp3Path[0]?wb->mp3Path:"(none)");
        }

        /* Music buffer = scene transition (backup detection) */
        if (playingFile[0] || primedFile[0]) {
            if (sz >= MUSIC_BUFFER_MIN_SIZE) {
                L("buf[%d] MUSIC (%lu bytes) -> scene exit, stopping voice", wb->id, sz);
                PS_StopNow();
                primedFile[0] = '\0';
                InterlockedIncrement(&primedGen);
            } else if (sz >= BIG_BUFFER_LOG_MIN_SIZE) {
                L("buf[%d] BIG CREATE (%lu bytes)", wb->id, sz);
            }
        }

        *ppBuf=(IDirectSoundBuffer*)wb;
    } else {if(ppBuf)*ppBuf=rb;}
    return hr;
}

static HRESULT __stdcall DS_GC(IDirectSound *p,void *c){WrapDS *w=(WrapDS*)p;return w->real->lpVtbl->GetCaps(w->real,c);}
static HRESULT __stdcall DS_DB(IDirectSound *p,IDirectSoundBuffer *src,IDirectSoundBuffer **dst){
    WrapDS *w=(WrapDS*)p;IDirectSoundBuffer *rs=src;
    if(src&&src->lpVtbl==&wbVtbl)rs=((WrapBuf*)src)->real;
    IDirectSoundBuffer *rd=NULL;
    HRESULT hr=w->real->lpVtbl->DuplicateSoundBuffer(w->real,rs,&rd);
    if(hr==0&&rd&&dst){WrapBuf *wb=(WrapBuf*)HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,sizeof(WrapBuf));wb->lpVtbl=&wbVtbl;wb->real=rd;wb->refCount=1;wb->id=nextBufId++;*dst=(IDirectSoundBuffer*)wb;}
    else{if(dst)*dst=rd;}return hr;
}
static HRESULT __stdcall DS_SC(IDirectSound *p,HWND h,DWORD l){WrapDS *w=(WrapDS*)p;return w->real->lpVtbl->SetCooperativeLevel(w->real,h,l);}
static HRESULT __stdcall DS_Co(IDirectSound *p){WrapDS *w=(WrapDS*)p;return w->real->lpVtbl->Compact(w->real);}
static HRESULT __stdcall DS_GSp(IDirectSound *p,DWORD *c){WrapDS *w=(WrapDS*)p;return w->real->lpVtbl->GetSpeakerConfig(w->real,c);}
static HRESULT __stdcall DS_SSp(IDirectSound *p,DWORD c){WrapDS *w=(WrapDS*)p;return w->real->lpVtbl->SetSpeakerConfig(w->real,c);}
static HRESULT __stdcall DS_In(IDirectSound *p,const GUID *g){WrapDS *w=(WrapDS*)p;return w->real->lpVtbl->Initialize(w->real,g);}

static DSVtbl wdsVtbl = {DS_QI,DS_AR,DS_Rl,DS_CSB,DS_GC,DS_DB,DS_SC,DS_Co,DS_GSp,DS_SSp,DS_In};

__declspec(dllexport) HRESULT WINAPI hook_DirectSoundCreate(const GUID *g,IDirectSound **pp,void *u){
    if(!real_DSCreate)return 0x80004005;
    IDirectSound *r=NULL;HRESULT hr=real_DSCreate(g,&r,u);
    if(hr==0&&r&&pp){WrapDS *w=(WrapDS*)HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,sizeof(WrapDS));w->lpVtbl=&wdsVtbl;w->real=r;w->refCount=1;*pp=(IDirectSound*)w;}
    else{if(pp)*pp=r;}return hr;
}

__attribute__((naked)) void fwd_DSEnumA(void){__asm__ __volatile__("movl %0,%%eax\ntestl %%eax,%%eax\njz 1f\njmp *%%eax\n1:xorl %%eax,%%eax\nret\n"::"m"(real_DSEnumA):"eax");}
__attribute__((naked)) void fwd_DSEnumW(void){__asm__ __volatile__("movl %0,%%eax\ntestl %%eax,%%eax\njz 1f\njmp *%%eax\n1:xorl %%eax,%%eax\nret\n"::"m"(real_DSEnumW):"eax");}
__attribute__((naked)) void fwd_DSCapCreate(void){__asm__ __volatile__("movl %0,%%eax\ntestl %%eax,%%eax\njz 1f\njmp *%%eax\n1:xorl %%eax,%%eax\nret\n"::"m"(real_DSCapCreate):"eax");}
__attribute__((naked)) void fwd_DSCapEnumA(void){__asm__ __volatile__("movl %0,%%eax\ntestl %%eax,%%eax\njz 1f\njmp *%%eax\n1:xorl %%eax,%%eax\nret\n"::"m"(real_DSCapEnumA):"eax");}
__attribute__((naked)) void fwd_DSCapEnumW(void){__asm__ __volatile__("movl %0,%%eax\ntestl %%eax,%%eax\njz 1f\njmp *%%eax\n1:xorl %%eax,%%eax\nret\n"::"m"(real_DSCapEnumW):"eax");}
__attribute__((naked)) void fwd_CanUnload(void){__asm__ __volatile__("movl %0,%%eax\ntestl %%eax,%%eax\njz 1f\njmp *%%eax\n1:xorl %%eax,%%eax\nret\n"::"m"(real_DllCanUnloadNow):"eax");}
__attribute__((naked)) void fwd_GetClass(void){__asm__ __volatile__("movl %0,%%eax\ntestl %%eax,%%eax\njz 1f\njmp *%%eax\n1:xorl %%eax,%%eax\nret\n"::"m"(real_DllGetClassObject):"eax");}
__attribute__((naked)) void fwd_DSCreate8(void){__asm__ __volatile__("movl %0,%%eax\ntestl %%eax,%%eax\njz 1f\njmp *%%eax\n1:xorl %%eax,%%eax\nret\n"::"m"(real_DSCreate8):"eax");}
__attribute__((naked)) void fwd_FullDuplex(void){__asm__ __volatile__("movl %0,%%eax\ntestl %%eax,%%eax\njz 1f\njmp *%%eax\n1:xorl %%eax,%%eax\nret\n"::"m"(real_DSFullDuplexCreate):"eax");}

BOOL WINAPI DllMain(HINSTANCE h, DWORD reason, LPVOID r) {
    (void)r;
    if(reason==DLL_PROCESS_ATTACH){
        DisableThreadLibraryCalls(h);
#if ENABLE_LOGGING
        InitializeCriticalSection(&logCS);
#endif
        InitializeCriticalSection(&pathCS);InitializeCriticalSection(&playCS);
        GetModuleFileNameA(h,gameDir,MAX_PATH);
        char *sl=strrchr(gameDir,'\\');if(sl)sl[1]='\0';
        char path[MAX_PATH];
        lstrcpyA(path, gameDir); lstrcatA(path, "dsound.shogun_audio_fix.orig.dll");
        hReal = LoadLibraryA(path);
        if (!hReal) {
            lstrcpyA(path, gameDir); lstrcatA(path, "dsound.dll.bak");
            hReal = LoadLibraryA(path);
        }
        if (!hReal) {
            GetSystemDirectoryA(path, MAX_PATH);
            lstrcatA(path, "\\dsound.dll");
            hReal = LoadLibraryA(path);
        }
        if(hReal){
            real_DSCreate=(DSCreate_t)GetProcAddress(hReal,"DirectSoundCreate");
            real_DSEnumA=GetProcAddress(hReal,"DirectSoundEnumerateA");
            real_DSEnumW=GetProcAddress(hReal,"DirectSoundEnumerateW");
            real_DSCapCreate=GetProcAddress(hReal,"DirectSoundCaptureCreate");
            real_DSCapEnumA=GetProcAddress(hReal,"DirectSoundCaptureEnumerateA");
            real_DSCapEnumW=GetProcAddress(hReal,"DirectSoundCaptureEnumerateW");
            real_DllCanUnloadNow=GetProcAddress(hReal,"DllCanUnloadNow");
            real_DllGetClassObject=GetProcAddress(hReal,"DllGetClassObject");
            real_DSCreate8=GetProcAddress(hReal,"DirectSoundCreate8");
            real_DSFullDuplexCreate=GetProcAddress(hReal,"DirectSoundFullDuplexCreate");
        }
#if ENABLE_LOGGING
        startTick=GetTickCount();
        char lp[MAX_PATH];lstrcpyA(lp,gameDir);lstrcatA(lp,"dsound_log.txt");
        logFile=fopen(lp,"w");
        if(logFile)L("=== dsound.dll proxy v19 (response+scene+advisor-done) ===");
#endif
        HookIAT();
    } else if(reason==DLL_PROCESS_DETACH){
        PS_StopNow();
#if ENABLE_LOGGING
        if(logFile){L("=== unloading ===");fclose(logFile);}
        DeleteCriticalSection(&logCS);
#endif
        DeleteCriticalSection(&pathCS);DeleteCriticalSection(&playCS);
        if(hWinmm)FreeLibrary(hWinmm);
        if(hReal)FreeLibrary(hReal);
    }
    return TRUE;
}
"""

DSOUND_DEF = """LIBRARY dsound
EXPORTS
    DirectSoundCreate          = hook_DirectSoundCreate @1
    DirectSoundEnumerateA      = fwd_DSEnumA @2
    DirectSoundEnumerateW      = fwd_DSEnumW @3
    DllCanUnloadNow            = fwd_CanUnload @4 PRIVATE
    DllGetClassObject          = fwd_GetClass @5 PRIVATE
    DirectSoundCaptureCreate   = fwd_DSCapCreate @6
    DirectSoundCaptureEnumerateA = fwd_DSCapEnumA @7
    DirectSoundCaptureEnumerateW = fwd_DSCapEnumW @8
    DirectSoundCreate8         = fwd_DSCreate8 @10
    DirectSoundFullDuplexCreate = fwd_FullDuplex @11
"""

BACKUP_DSOUND_NAME = "dsound.shogun_audio_fix.orig.dll"
LEGACY_BACKUP_DSOUND_NAME = "dsound.dll.bak"

def find_ffmpeg():
    for cmd in ["ffmpeg","ffmpeg.exe",
                r"F:\Games\ffmpeg\bin\ffmpeg.exe",
                r"C:\ffmpeg\bin\ffmpeg.exe"]:
        try:
            r=subprocess.run([cmd,"-version"],capture_output=True,timeout=5)
            if r.returncode==0: return cmd
        except: pass
    return None

def find_compiler():
    for cmd in ["i686-w64-mingw32-gcc","gcc","cc",
                r"F:\Games\w64devkit\bin\gcc.exe",
                r"C:\w64devkit\bin\gcc.exe"]:
        try:
            r=subprocess.run([cmd,"--version"],capture_output=True,timeout=5)
            if r.returncode==0: return cmd
        except: pass
    return None

def compile_dll(c_path,def_path,dll_path,cc):
    cmd=[cc,"-shared","-O2","-o",str(dll_path),str(c_path),str(def_path),"-Wl,--enable-stdcall-fixup"]
    print("  {}".format(" ".join(cmd)))
    env=os.environ.copy()
    cc_parent=str(Path(cc).resolve().parent)
    env["PATH"]=cc_parent+os.pathsep+env.get("PATH","")
    r=subprocess.run(cmd,capture_output=True,text=True,timeout=60,env=env)
    if r.returncode!=0:
        print("  FAILED!")
        for line in (r.stderr or "").strip().split('\n')[-15:]: print("    "+line)
        return False
    if dll_path.exists(): print("  OK! {} bytes".format(dll_path.stat().st_size)); return True
    return False

def is_our_proxy_dsound(path):
    try:
        data = Path(path).read_bytes()
    except OSError:
        return False
    markers = (
        b"dsound.dll proxy v",
        b"shogun_audio_fix.orig.dll",
        b"response+scene+advisor-ui",
    )
    return any(marker in data for marker in markers)

def convert_mp3s(game_dir, ffmpeg):
    seen=set(); mp3s=[]
    for f in sorted(game_dir.rglob("*")):
        if f.suffix.lower()==".mp3" and str(f).lower() not in seen:
            seen.add(str(f).lower()); mp3s.append(f)
    print("  {} MP3s".format(len(mp3s)))
    n=0
    for i,mp3 in enumerate(mp3s,1):
        wav=Path(str(mp3)+".wav")
        if wav.exists(): n+=1; continue
        r=subprocess.run([ffmpeg,"-y","-i",str(mp3),"-acodec","pcm_s16le","-ar","22050","-ac","1",str(wav)],capture_output=True,timeout=30)
        if r.returncode==0 and wav.exists(): n+=1
        if i%50==0: print("    {}/{}".format(i,len(mp3s)))
    print("  {} WAVs ready".format(n)); return n

def cleanup_wavs(game_dir):
    removed = 0
    for w in game_dir.rglob("*"):
        if w.is_file() and w.name.lower().endswith(".mp3.wav"):
            w.unlink()
            removed += 1
    return removed

def restore_dsound(game_dir):
    ds = game_dir/"dsound.dll"
    if ds.exists():
        ds.unlink()
        print("Removed dsound.dll")
    for name in (BACKUP_DSOUND_NAME, LEGACY_BACKUP_DSOUND_NAME):
        bak = game_dir/name
        if bak.exists():
            if is_our_proxy_dsound(bak):
                bak.unlink()
                print("Removed stale proxy backup {}".format(name))
                continue
            shutil.move(str(bak), str(ds))
            print("Restored {}".format(name))
            break

def backup_existing_dsound(game_dir):
    ds = game_dir/"dsound.dll"
    preferred = game_dir/BACKUP_DSOUND_NAME
    legacy = game_dir/LEGACY_BACKUP_DSOUND_NAME
    if ds.exists() and not preferred.exists() and not legacy.exists():
        if is_our_proxy_dsound(ds):
            print("  Existing dsound.dll is already this proxy; no backup needed")
            return
        shutil.copy2(str(ds), str(preferred))
        print("  Backed up existing dsound.dll -> {}".format(BACKUP_DSOUND_NAME))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("game_dir")
    parser.add_argument("--restore",action="store_true")
    parser.add_argument("--debug-log",action="store_true")
    args=parser.parse_args()
    print("="*62)
    print("  Shogun: Total War - Throne Room Audio Fix (v1)")
    print("="*62)
    game_dir=Path(args.game_dir)
    if not game_dir.exists(): sys.exit("Not found")
    if args.restore:
        for fn in ["winmm.dll","winmm.dll.bak"]:
            p=game_dir/fn
            if p.exists(): p.unlink(); print("Removed "+fn)
        restore_dsound(game_dir)
        removed = cleanup_wavs(game_dir)
        print("Removed {} generated WAV sidecars".format(removed))
        print("Done."); sys.exit(0)
    print("\nStep 1: Convert MP3 -> WAV")
    ff=find_ffmpeg()
    if not ff: sys.exit("ffmpeg not found!")
    convert_mp3s(game_dir, ff)
    print("\nStep 2: Build proxy DLL")
    backup_existing_dsound(game_dir)
    for fn in ["winmm.dll","winmm.dll.bak"]:
        p=game_dir/fn
        if p.exists(): p.unlink()
    work=Path(tempfile.mkdtemp(prefix="shogun_"))
    dsound_c = DSOUND_C.replace("__ENABLE_LOGGING__", "1" if args.debug_log else "0")
    (work/"dsound.c").write_text(dsound_c);(work/"dsound.def").write_text(DSOUND_DEF)
    cc=find_compiler()
    if not cc: sys.exit("No compiler!")
    print("  Compiler: "+cc)
    if not compile_dll(work/"dsound.c",work/"dsound.def",work/"dsound.dll",cc): sys.exit(1)
    shutil.copy2(str(work/"dsound.dll"),str(game_dir/"dsound.dll"))
    shutil.rmtree(str(work),ignore_errors=True)
    print("\n"+"="*62)
    print("  FIX INSTALLED! Test the throne room.")
    print('  To restore: python shogun_audio_fix.py "{}" --restore'.format(game_dir))

if __name__=="__main__": main()
