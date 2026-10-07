# tetkiwam2dreamcast

Tetris Kiwamemichi (Success, 2004, Naomi GD-ROM GDL-0020, MAME set `tetkiwam`) on a
real Dreamcast. This repo has the build method only: no game data, ROMs, BIOS or
disc images. Bring your own dump. Working notes live in `docs/kb/`;
`docs/kb/00-status.md` is the narrative index.

> **This is a conversion, not a port.** The arcade disc already ships a complete
> Dreamcast build of the game: Success left a DC executable and filesystem inside
> the encrypted Naomi image. No game code is rewritten or recompiled here, and
> the only code patch on the GDI is one byte that switches on the game's own free-play mode (the CD-R build adds three more so it runs from a CD). The work is extracting that build and laying it out on a disc the real
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

Requires `chdman` (`brew install rom-tools`, v0.289 used), `clang++`, Python 3;
the CDI also needs mkdcdisc (below).

```
python3 build_gdi.py            # -> build/gdi/tetris.gdi + track01..04
```

Or `make` (same build), `make verify` (checks the reference SHA1s below),
`make cdi` (CD-R image, see below), `make release` (`[GDI]` and `[CDI]` zips,
local only, never upload), `make deploy CARD=/Volumes/GDEMU/NN`.

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

Optional, same rule: drop `0GDTEX.PVR` at the repo root (bare PVRT header,
RGB565, rectangle layout 0x09, 256×256, 131088 B) and the build replaces the
disc art, the picture the DC BIOS disc menu and the GDEMU menu show for the
disc. The shipped `0GDTEX.PVR` is a leftover: a picture of Success's *Pokekano*
CD, not Tetris. The build Morton-twiddles the new pixels over the donor's extent
in place (same mechanism as senkosp2dreamcast `make_gdi.py` `patch_gdtex`;
twiddle order per Flycast `core/rend/texconv.cpp` `twiddle_slow`), keeps the
donor's 32-byte GBIX+PVRT header and flips only its pixel-format byte from
ARGB1555 to RGB565, the format the sibling's hardware-verified art uses. The
cover art is copyrighted, so it is gitignored and not in this repo. Absent, the
donor art stays and track03 is byte-identical to the row above. Checked offline
(2026-10-04): the delta is confined to that extent, detwiddling the on-disc
bytes gives the input pixels exactly, and the same detwiddle turns the donor's
own art into a correct picture (twiddle-order control). Confirmed on real
hardware (GDEMU, user report, 2026-10-04).

CD-R: `make cdi` → `build/cdi/tetris.cdi`, a self-booting audio/data MIL-CD
for burning, plus burn notes in `README.txt`. It needs
[mkdcdisc](https://gitlab.com/simulant/mkdcdisc) (v0.0.4; set `MKDCDISC=` if it
isn't at `../senkosp2dreamcast/tools/mkdcdisc/build/mkdcdisc`). `make_cdi.py`
takes the files from the built GDI, so the art, title and free play carry over.
mkdcdisc writes its own CD IP.BIN (with this disc's title and fields, and
`iplogo.mr` if present) and scrambles the boot file. senkosp2dreamcast found
on hardware that a retail GD IP.BIN won't boot from CD. The CD copy of
`1ST_READ.BIN` gets three more patches, since the game (Katana) assumes it
booted from a GD-ROM. Its four hardcoded GD sector addresses (45150
×3, 45166) move to the CD data track (−33298, the old selfboot "binhack"). Its
mount-time check that the disc type is GD-ROM (`0x80`, at `0x8c010aac`) is
replaced by the call it never makes: the BIOS sector-mode syscall, set to
CD-ROM XA (track type 2048, as KOS and DreamShell do). Without it the BIOS
reads the CD's Mode 2 Form 1 track in GD Mode 1. Flycast doesn't check that,
but GDEMU showed only a black screen after the TM logo (round 1). And at
entry it unlocks the G1 bus to the drive (size to `0xa05f74e4`, then read the
whole BIOS), as KOS `cdrom_init` and the scene's binhack `IP.HAK` do. Without
it the game's first GD command hung on GDEMU (round 4), and Flycast doesn't
model the lock.
The CDI's IP.BIN region is mkdcdisc's `JUE`, not the GD's `J`. Checked in
Flycast with the real BIOS (2026-10-05): every read asks for Mode 2 Form 1, and it
plays into a 1P match. **Hardware: boots and plays on GDEMU (round 5, user
report, 2026-10-07)**, after four rounds of a black screen after the TM logo
(rounds 1–4). A burned CD-R is still untested. Details: `docs/kb/cdi.md`.

Always on: the build replaces IP.BIN's game title (offset 0x80, 128 bytes,
space-padded; Flycast `core/reios/reios.h` `ip_meta_t.software_name`, makeip
`src/field.c` "Game Title") with `TETRIS KIWAMEMICHI`. The shipped title is
Sega's "THIS IS A SAMPLE DISK FOR USE IN THE OFFICE ONLY / DO NOT SELL / DO NOT
CARRY OUT FROM THE OFFICE", and that's what GDEMU menus and Flycast display. The header
CRC at 0x20 covers only 0x40–0x4F (makeip `src/crc.c` `update_crc`), so nothing
else needs fixing up. Compared with 0.2.0, track03 differs only in 0x80–0xFF.
Confirmed on real hardware (GDEMU, user report, 2026-10-04).

Always on: free play. The game's coin manager already has a free-play flag
(object `+0x980`, copied every frame to `+0x904`). Its credit check (`0x8c087818`)
and credit spend (`0x8c0877a0`) return "OK" straight away when the flag is set,
and the attract overlay switches from INSERT COIN(S) / CREDIT(S) to the game's
own PRESS START BUTTON / FREE PLAY art. The Naomi build would set that flag from
coin setting #27, which is what Flycast's "Naomi Free Play" writes
(`core/hw/naomi/naomi_flashrom.cpp`, EEPROM byte 9 = 26). This DC build has no
EEPROM and its init stores 0. `build_gdi.py` changes that store in `1ST_READ.BIN`
at `0x8c0845e2` from `mov.l r3,@(r0,r12)` (r3 = 0) to `mov.l r1,@(r0,r12)`
(r1 = 1). That is one byte, `0x36` → `0x16` at file offset `0x745e2`, and the
original byte is asserted first. track04 differs from 0.3.0 in that byte only.
Checked in Flycast with the real BIOS (2026-10-04), with the stock build as the
control: the patched attract shows FREE PLAY and Start goes from the title to
play-style select with 0 credits. The stock build stays on INSERT COIN(S) /
CREDIT(S) 0 under the same scripted Start presses. Confirmed on real hardware
(GDEMU, user report, 2026-10-04).

Reference SHA1s of a verified build:

| file | sha1 |
|---|---|
| tetris.gdi | `1d6069f79206f488393963711ad6859a134c6b8f` |
| track01.bin | `5cf394175d4caad3b37b8f4ec213cb7b81d9a71f` |
| track02.raw | `6030e25dac2e9c0237aaf908b5037ee16503e0c0` |
| track03.iso | `82f8925aa94dd2ac266acf5cfae37dfb5ec71444` |
| track03.iso with `iplogo.mr` | `58870f766fa136f5a8fb760dad3cfd23b1bc9bed` |
| track03.iso with `iplogo.mr` + `0GDTEX.PVR` (0.3.0) | `05ab2d08d33d637e8f73f971d8387af6321fe274` |
| track04.iso (free play, 0.4.0) | `2718605b6947bad281ea81283212cccb1f29d534` |
| track04.iso before free play (≤ 0.3.0) | `5c18e14e53b922e6abc57e84e0bf741dd76f0d0d` |

Before the title patch (up to tag 0.2.0) the three track03 rows were
`d73e0903…`, `736cbb18…` (0.1.0) and `2157c4ee…` (0.2.0).

## Play

- Free play: no coins needed, Start starts. (Before free play, Y inserted a coin.)
- GDEMU/ODE: copy `build/gdi/` to the SD card. Run `dot_clean` on it first, since
  macOS `._*` files break GDEMU.
- CD-R: burn `build/cdi/tetris.cdi` as a disc image (DiscJuggler, Alcohol 120%), slow (≤ 8x).
  Late Dreamcasts that block MIL-CD can't boot any burned CD.
- The GDI is region `J` only, so a US/EU console needs a region-free BIOS or ODE.

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
| CDI (burned disc, `make cdi`) | ✅ Flycast + real BIOS → in-game, 2026-10-05; ✅ GDEMU round 5 (G1 bus unlock), boots and plays — user report, 2026-10-07, 0.5.0 (rounds 1–4 black: `docs/kb/cdi.md`); ⬜ CD-R |
| SEGA TM-screen logo (`iplogo.mr`) | ✅ Flycast + real BIOS; ✅ GDEMU — user report, 2026-10-04 |
| Disc art in BIOS / GDEMU menu (`0GDTEX.PVR`) | ✅ offline byte checks; ✅ GDEMU — user report, 2026-10-04 |
| Game title in IP.BIN (`TETRIS KIWAMEMICHI`) | ✅ offline byte diff + Flycast real-BIOS boot; ✅ GDEMU — user report, 2026-10-04 |
| Free play (1-byte `1ST_READ.BIN` patch) | ✅ Flycast + real BIOS, stock-build control; ✅ GDEMU — user report, 2026-10-04 |
