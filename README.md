# tetkiwam2dreamcast

Tetris Kiwamemichi (Success, 2004, Naomi GD-ROM GDL-0020, MAME set `tetkiwam`) on a
real Dreamcast. This repo has the build method only: no game data, ROMs, BIOS or
disc images. Bring your own dump.

> **This is a conversion, not a port.** The arcade disc already ships a complete
> Dreamcast build of the game: Success left a DC executable and filesystem inside
> the encrypted Naomi image. No game code is rewritten, patched or recompiled
> here. The work is extracting that build and laying it out on a disc the real
> Dreamcast BIOS will boot. As far as we know, this is the first time it has
> been confirmed booting on real hardware (GDEMU, 2026-10-03).

## How it works

The arcade disc's `TETRIS.BIN` is the Naomi DIMM image. You decrypt it with the
DES key from the game's security PIC (`317-5093-jpn`, key `62790B91859854C7`).
The first 0x500 bytes are a Naomi header. Everything after that is a complete
Dreamcast GD track 3: a DC IP.BIN (Sega's 2002 SDK "sample disk" header, boot
file `1ST_READ.BIN`, region `J`) plus an ISO9660 filesystem with absolute LBAs
starting at 45000 ([TCRF Notes page](https://tcrf.net/Notes:Tetris_Kiwamemichi_(Arcade))).

**Trimming alone doesn't boot on the real BIOS.** A 3-track GDI of the trimmed
image falls through to the BIOS menu in Flycast with a real `dc_boot.bin`, before
the license screen appears. Flycast's HLE BIOS (reios) boots it, so the game is
fine. What fixes it is moving `1ST_READ.BIN` to the first sector of a last data
track at LBA 450000, which is the same layout the Atomiswave→DC ports use
(cleopatra `phase4-conversion.md` B4). A bisect in Flycast (2026-10-03) showed
this is the only change needed. The original IP.BIN and the arcade disc's own
tracks 1–2 work unchanged. The control disc was Dolphin Blue on the same
Flycast + BIOS path.

## Build

Requires `chdman` (`brew install rom-tools`, v0.289 used), `clang++`, Python 3.

```
python3 build_gdi.py            # -> build/gdi/tetris.gdi + track01..04
```

It reads `tetkiwam.zip` (PIC) and `tetkiwam/gdl-0020.chd` from
`../naomi2dreamcast/naomi`. Set `NAOMI_DIR=` to point it somewhere else.
`tools/extract_dat.cpp` and `tools/des_block.c` handle the GD file location and
the DES, both transcribed from Flycast `core/hw/naomi/gdcartridge.cpp`, plus an
`EXTRACT_NAME` override that picks which disc file to decrypt.

Optional: drop `iplogo.mr` at the repo root (Sega MR format, 320×90, ≤ 8 KB) and
the build writes it into IP.BIN's logo slot, so the SEGA licence ("TM") screen
shows a logo instead of blank space. That slot is at IP.BIN offset 0x3820
(makeip `src/mr.c` `MR_OFFSET`; mc.pp.se/dc/ip.bin.html lists 0x3800–0x5FFF as
modifiable bootstrap). The shipped IP.BIN leaves it zeroed, and its licence code
holds the slot pointer `0x8c00b820` at 0x083c, so the logo is drawn as-is. We use
the same NAOMI GD-ROM SYSTEM logo as senkosp2dreamcast. It is Sega trademark art,
so it is gitignored and not in this repo. Absent, track03 is byte-identical to
the build before this option existed. Checked in Flycast with the real BIOS
(2026-10-04): the licence screen shows the logo (dumped from the guest
framebuffer, since the BIOS draws that screen in 32-bit 0888 and Flycast's own
screenshot path only sees PVR-rendered frames). Confirmed on real hardware
(GDEMU, user report, 2026-10-04).

Reference SHA1s of a verified build:

| file | sha1 |
|---|---|
| tetris.gdi | `1d6069f79206f488393963711ad6859a134c6b8f` |
| track01.bin | `5cf394175d4caad3b37b8f4ec213cb7b81d9a71f` |
| track02.raw | `6030e25dac2e9c0237aaf908b5037ee16503e0c0` |
| track03.iso | `d73e09037ee2baac87c0a56242d1003d82f276e6` |
| track03.iso with `iplogo.mr` | `736cbb18b0c39acc395a46b0692d8ae25dfa0e8f` |
| track04.iso | `5c18e14e53b922e6abc57e84e0bf741dd76f0d0d` |

## Play

- Coin-op is still active (not free-play): **Y inserts a coin**, Start starts.
- GDEMU/ODE: copy `build/gdi/` to the SD card. Run `dot_clean` on it first, since
  macOS `._*` files break GDEMU.
- The disc is region `J` only, so a US/EU console needs a region-free BIOS or ODE.

## Prior art & credits

- **The Cutting Room Floor** found the leftover Dreamcast build and published the
  decrypt key and the trim/GDI recipe:
  [Tetris Kiwamemichi (Arcade)](https://tcrf.net/Tetris_Kiwamemichi_(Arcade)) and
  [Notes page](https://tcrf.net/Notes:Tetris_Kiwamemichi_(Arcade)). Their Notes page
  ends: "This GDI should run in Flycast and DEmul, however I have not yet heard test results on real hardware." (checked 2026-10-03). This repo
  adds the track-4 `1ST_READ.BIN` relocation, which the real BIOS needs, and a
  scripted build.
- **Flycast** (flyinghead) and **MAME** (`naomigd.cpp`, Olivier Galibert) are the
  source of the GD-ROM file lookup and Naomi DES code in `tools/`.
- **megavolt85's Atomiswave→DC ports** (Dolphin Blue, Sushi Bar) showed the
  boot-file-in-the-last-data-track layout, documented in the cfp2dreamcast port.

## License

GPL-2.0 (see `LICENSE`), because `tools/` is derived from Flycast (GPL-2.0),
which took that code from MAME (BSD-3-Clause). No game data is included or
distributed. Tetris Kiwamemichi belongs to its rights holders.

## Status

| check | result |
|---|---|
| Flycast, real BIOS → title + attract | ✅ 2026-10-03 |
| Real DC hardware (GDEMU) | ✅ works — user report, 2026-10-03 |
| CDI (burned disc) | ⬜ not built |
| SEGA TM-screen logo (`iplogo.mr`) | ✅ Flycast + real BIOS; ✅ GDEMU — user report, 2026-10-04 |
