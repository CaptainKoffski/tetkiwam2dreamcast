# Project status

**Updated:** 2026-10-10 — Release 0.6.0: runs from DreamShell's ISO Loader on an SD card (DMA reads pass a P1 buffer address; the game runs with the MMU on), DreamShell-verified; before that,
Release 0.5.0: CDI next to the GDI, plays on GDEMU; CD-R burn owed (see below). **Release 0.5.0 (tag, on `main`): the shipped
Dreamcast build of Tetris Kiwamemichi boots on real hardware (GDEMU) with
the NAOMI GD-ROM SYSTEM logo on the SEGA TM screen, the Tetris cover
in the BIOS / GDEMU disc menu, its own name in the disc header, and free
play, as a GDI and (0.5.0) as a CD-R image (CDI).** Scope is a
conversion, not a port (README): the arcade GD-ROM carries a finished DC
build; we decrypt it, relocate `1ST_READ.BIN` to a last data track,
(0.1.0) fill IP.BIN's empty logo slot, (0.2.0) swap the disc art and
(0.3.0) replace the sample-disk title and (0.4.0) switch on the game's
own free-play flag (one byte in `1ST_READ.BIN`); (0.5.0) the CDI re-masters
that build for CD-R with three CD-only patches. Honest limit: single-rig evidence —
one console, one GDEMU, one user report per round.

Layout mirrors senkosp2dreamcast: this file is the narrative index,
`tooling.md` holds recipes/citations/checksums, one file per step holds
the full record (`iplogo.md`, `gdtex.md`, `freeplay.md`).

**DREAMSHELL SD CLOSED ON HARDWARE (2026-10-10, user reports "works on DreamShell
now", then "works on GDEMU too"); Release 0.6.0.** Root cause and fix found 2026-10-09: Reports: black screen, no sound, after isoldr's loader text, from
ISO Loader with default settings (SD on the serial port, VGA, DreamShell launched
from GDEMU). The game turns the SH4 MMU on for its store queues, and its Katana gdc
read passes DMA buffers as physical `0x0c…` addresses. isoldr's SD firmware has
no DMA, so it copies sectors there with the CPU, takes a TLB miss, and lands in
the game's crash handler. Fix: one byte in `1ST_READ.BIN` (mask literal
`0x1fffffff` → `0xffffffff` at `0x8c010508`), so DMA reads pass the P1 buffer
address. Holly masks `SB_GDSTAR` to bits 28:5, so real DMA is unchanged.

Round 1's serial-console patch was the wrong cause (still black on hardware) and
is dropped: isoldr re-inits SPI after the game's SCIF setup.

Found with a new SD-card model on the fork's serial port running DreamShell's real
`sd.bin`. Plain Flycast plays every variant. The cache/MMU (strict) build
reproduces the hang and shows the fix playing. GDI/CDI real-BIOS legs unchanged.
track04 `27bc2a19…`; track01–03 and `.gdi` unchanged. Full record: `dreamshell.md`.

**CDI CLOSED ON GDEMU (2026-10-07, round 5 E, user report "E works, game shows
up on GDEMU" … "I actually played a bit"); Release 0.5.0 PROMOTED, tag pushed.
G1 bus unlock.** Round 4 (serial trace)
showed the CDI's first game GD command (CMD_INIT) stuck in a data phase on
GDEMU. The scene's binhack `IP.HAK` bootstrap, decoded, unlocks Holly's G1
bus first (size to `0xa05f74e4`, read the whole BIOS), as KOS `cdrom_init` does.
Katana doesn't, and Flycast ignores the register. Patch 3 in `make_cdi.py`
does it at entry. Flycast still plays; on GDEMU the release CDI (E) now shows
the game and plays, so the traced F wasn't needed. GDI unchanged (track03
`05ab2d08…`, track04 `2718605b…` = 0.4.0). CD-R burn still owed. Existing GDI→CDI tools can't convert this game as-is:
binhack fixes 1 of the 4 GDFS FAD words. `cdi.md` §Existing tools.

**CDI GDEMU round 2 FAILED too (2026-10-05)**: same black screen after TM,
with the read-mode fix. Cache state ruled out in a strict (cache-model)
Flycast. Round 3 is a diagnostic: an entry marker on the GDI (control) and on
the CDI, in `build/diag-r3/`, to see whether the game starts at all on
hardware. `cdi.md`.

**CDI round 2 BUILT (2026-10-05): GDEMU round 1 FAILED, fix
emulator-verified, hardware owed.** Round 1 showed a black screen after the TM
logo. Cause found with a new fork log (GDREAD): after its drive init the game
reads in Mode 1 (CD_READ expected data type 2), and this CD is Mode 2 Form 1.
The game never calls the sector-mode syscall, and Flycast ignores the field.
Fix in `make_cdi.py`: gdFsInit's GD-only disc-type check becomes a call to
sector-mode with KOS's XA params (2048). Flycast: 145/145 reads type 4, into a 1P
match. `cdi.md`.

**CDI SHIPPED (2026-10-05, emulator-verified; hardware owed): `make
release` now builds `[GDI]` and `[CDI] Tetris Kiwamemichi.zip`, as in the
sibling.** `make_cdi.py` re-masters the built GDI's files with mkdcdisc (CD IP
+ scramble, the sibling's GDEMU-proven chain). Two CD-only patches to
`1ST_READ.BIN`: the binhack-style LBA shift of the GDFS's four hardcoded GD FADs
(45150 ×3, 45166 → −33298), and the gdFsInit disc-type check (`== 0x80`
GD-ROM) made always-true (replaced in round 2, see above). Without the second, the game's first FS read is FAD 0
and it stops on `vmsFileDeviceClass::setDirChashe`. Flycast + real BIOS: into a
1P match, 554 reads, 0 misses. GDI unchanged (`make verify` OK). Owed: GDEMU,
then a burned CD-R. Full record: `cdi.md`.

**FREE PLAY CLOSED (2026-10-04, operator hardware verdict "works on
GDEMU"); Release 0.4.0 PROMOTED, tag pushed. No coins needed.** The DC build already has a free-play flag in its coin manager
(`+0x980` → `+0x904`, checked first by has-credit `0x8c087818` and
spend-credit `0x8c0877a0`). Init hardcodes it to 0. `build_gdi.py` patches
that one store in `1ST_READ.BIN` (offset 0x745e2, `0x36`→`0x16`) so it
stores 1. track04 sha1 `2718605b…`, other tracks unchanged. Flycast real
BIOS with the stock build as control: FREE PLAY overlay, and Start reaches
play-style select with 0 credits. GDEMU: works (user report), one-round
close. track04 `2718605b…` = **0.4.0 track04**; gdi + tracks 01/02/03
unchanged from 0.3.0. Full record: `freeplay.md`.

**GAME TITLE CLOSED (2026-10-04, operator hardware verdict "works on
GDEMU"); Release 0.3.0 PROMOTED, tag pushed.** IP.BIN's
title field (0x80, 128 B) shipped as Sega's "THIS IS A SAMPLE DISK FOR USE
IN THE OFFICE ONLY / DO NOT SELL / ...", which GDEMU menus show.
`build_gdi.py` now always writes `TETRIS KIWAMEMICHI` there (Flycast
`core/reios/reios.h` `ip_meta_t.software_name`; makeip `src/field.c`). The
header CRC covers only 0x40–0x4F (makeip `src/crc.c`), so no fixup. Delta vs
0.2.0 track03 = 78 bytes inside 0x81–0xDF; with both optional files track03
sha1 = `05ab2d08…`. Flycast real BIOS → attract, unchanged. GDEMU: works
(user report), one-round close. track03 `05ab2d08…` = **0.3.0 track03**;
gdi + tracks 01/02/04 unchanged since the base build.

**GDTEX CLOSED (2026-10-04, operator hardware verdict "Work perfectly on
the HW"); Release 0.2.0 PROMOTED, tag pushed.** Tetris cover art in the BIOS / GDEMU disc menu.** Same move as
senkosp2dreamcast Task #28: the operator's `0GDTEX.PVR` (bare PVRT, RGB565
rectangle 256×256, gitignored) is Morton-twiddled over the disc's own
`0GDTEX.PVR` extent (LBA 81210) in place by `build_gdi.py`. One difference
from the sibling: this donor stores its art ARGB1555, so the header's
pixel-format byte is flipped to RGB565 instead of kept verbatim. The
shipped art turned out to be a leftover *Pokekano* CD picture, and
detwiddling it cleanly with the same bit order is the twiddle-order
control. Delta confined to the extent, round trip exact, control build
without the file = 0.1.0 track03 exactly; candidate track03 sha1
`2157c4ee…` = **0.2.0 track03**; gdi + tracks 01/02/04 unchanged since
the base build. Full record: `gdtex.md`.

**IPLOGO CLOSED (2026-10-04, operator hardware verdict): "works on
GDEMU" — the NAOMI logo on the SEGA TM screen holds on real silicon,
one-round close.** **Release 0.1.0 PROMOTED:** track03 sha1 =
`736cbb18b0c39acc395a46b0692d8ae25dfa0e8f` (first track03 change since
the base build), tracks 01/02/04 + gdi unchanged; branch `iplogo`
fast-forwarded into `main`, annotated tag `0.1.0`, both pushed; respin
from defaults byte-identical (needs the gitignored `iplogo.mr` at repo
root). Full record: `iplogo.md`.

**IPLOGO ROUND 1 SHIPPED (2026-10-04, branch `iplogo`): NAOMI logo on
the SEGA TM screen.** Same mechanism as senkosp2dreamcast T12: the
screen's image is IP.BIN's MR-logo slot (track03 offset 0x3820, 8192 B —
makeip `src/mr.c:39` MR_OFFSET), measured as exactly that zero run in the
shipped IP.BIN, with the license code's `0x8c00b820` literal at 0x083c
pointing at it. Fix: `build_gdi.py` writes the gitignored `iplogo.mr`
(same file as the sibling; decoded + viewed = NAOMI™ GD-ROM SYSTEM logo,
320×90/63 colors/6807 B) into the slot before track03 is written. Control
build without the file = the README's prior track03 sha1 exactly; with
it, only 0x3820..0x52b5 differ. **Beyond the sibling's round 1:** the
license screen was actually seen in the emulator — real BIOS in the
instrumented Flycast fork, guest-framebuffer dump extended to 0888 for
the purpose (fork commit `ab2196447`). Hardware round owed: TM screen
shows the logo + boot regression.

**BASE BUILD (2026-10-03): DC-bootable GDI from the arcade GD-ROM; GDEMU
confirmed by user report the same day.** Record is the README ("How it
works") and the git log (`75fc7b6`, `de57383`); no KB existed yet.
