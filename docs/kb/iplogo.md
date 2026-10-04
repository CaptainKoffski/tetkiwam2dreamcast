# IPLOGO — NAOMI logo on the SEGA TM screen (2026-10-04, branch `iplogo`)

**Funding:** operator, 2026-10-04: "add the custom SEGA TM splash screen
just like we did in ../senkosp2dreamcast". Same file, same slot, same
verdict path as the sibling's T12; the new ground is the emulator capture.

## Recon — this IP.BIN carries the slot empty, like the sibling's donor

- The shipped IP.BIN is Sega's 2002 SDK sample-disk header
  (`SEGA ENTERPRISES 7007 GD-ROM1/1 J … T0000M V0.800 20021024`), i.e.
  the stock bootstrap with no logo: measured an exactly 8192-byte zero run
  at track03 0x3820..0x5820 and the literal `0x8c00b820`
  (= 0x8c008000 + 0x3820) at IP.BIN offset 0x083c — identical to the
  sibling's Dolphin Blue donor findings, so the same license code reads
  the same slot.
- Slot mechanism, cited: makeip `src/mr.c:36` `MR_MAX_SIZE 8192`,
  `:39` `MR_OFFSET 0x3820`, `:436` `memcpy(ip + MR_OFFSET, …)` (copy read
  at `../senkosp2dreamcast/tools/kos/utils/makeip/src/mr.c`);
  mc.pp.se/dc/ip.bin.html (Marcus Comstedt): 0x3800–0x5FFF "Bootstrap 1
  … can be modified", license code 0x0300–0x36FF immutable.

## Fix — inline in build_gdi.py

`iso` is already a bytearray in memory, so the patch is a slice write
before track03 is dumped (no file reopen, unlike the sibling's
`patch_iplogo`): optional `iplogo.mr` at repo root (gitignored — Sega
trademark art, same rule as the sibling's `0GDTEX.*`); asserts `MR`
signature, header size field == file size, ≤ 8192 B, and that the slot is
still the zero run (IP.BIN-swap tripwire); writes the file at 0x3820.
Absent → build byte-identical (control below).

## Round-1 verification

- **File is the real thing:** copied from `../senkosp2dreamcast/iplogo.mr`
  (operator-supplied there; dreamcast-talk file 18794). Decoded with the
  makeip `gimp/file-mr.py` RLE scheme (stdlib port, `tooling.md`):
  28800/28800 px, 320×90, 63 colors, 6807 B; viewed = NAOMI™ GD-ROM SYSTEM
  logo (black/orange).
- **Control build (working-style rule 2):** `iplogo.mr` moved aside,
  rebuilt to scratch: track03 sha1 `d73e0903…` == the README's prior
  reference exactly. With the file: 6186 differing bytes, all inside
  0x3820..0x52b5; slot == file + 1385 zero pad, compared outside the
  build. Tracks 01/02/04 + `tetris.gdi` sha1-identical either way.
- **Emulator, real BIOS (`UseReios = no`, `dc_boot.bin` in Flycast's
  data dir), instrumented fork `../flycast4naomi2dreamcast`:**
  1. `$FLYCAST_SHOT` (PVR-rendered frames, 1/s): swirl ~7–11 s, three
     plain-grey frames ~12–14 s, then the game. The license screen is
     drawn by the IP.BIN code straight into the framebuffer, so the
     TA-render readback shows only the background — the same limit the
     sibling hit (its T12 banked no frame).
  2. `$FLYCAST_SHOT_RAWFB` + SIGUSR2 every 0.5 s: the four signals in the
     license window logged `RAWFB: fb_depth not packed-565,
     FB_R_CTRL=0000000d` — fb_depth 3 = `fbde_C888`, 32-bit 0888
     (`core/hw/pvr/pvr_regs.h:103`). **Control through the same path:**
     the sibling's hardware-verified `build/disc.gdi` logged the same
     four skips — tool limit, not our bytes.
  3. Extended the fork's `rawfbWatcher` to unpack 0888 (R=23:16 G=15:8
     B=7:0, per `core/rend/TexCache.cpp:860` `fbde_C888`), incremental
     `cmake --build build` ~4 s, recaptured: **the frame at ~12 s is the
     SEGA licence screen — "PRODUCED BY OR UNDER LICENSE FROM SEGA
     ENTERPRISES, LTD." with the NAOMI GD-ROM SYSTEM logo below it.**
     Boot continues into the game (game framebuffer from ~15 s, as
     before). Frame kept at `build/tm_screen.png` (gitignored, trademark
     art). Fork change committed together with the operator's RAWFB
     dumper as `ab2196447`, pushed.
- **Candidate:** track03 sha1 `736cbb18b0c39acc395a46b0692d8ae25dfa0e8f`;
  everything else unchanged. Commit `7870158`.

## Hardware verdict (2026-10-04) — PASS; IPLOGO CLOSED, release 0.1.0

**Operator:** "works on GDEMU". One-round close. README verdict commit
`72f50d4`; `main` fast-forwarded (linear history, no merge commit),
annotated tag `0.1.0`, both pushed; branch `iplogo` deleted. Rebuild note:
`iplogo.mr` must be at repo root to reproduce the 0.1.0 track03; absent,
the base-build track03 comes back by design.

### Blast radius of the fork change (operator question, 2026-10-04)

Dev tool only: the 0888 case runs only with `$FLYCAST_SHOT_RAWFB` set and
SIGUSR2 received; the 565 branch is unchanged; reads go through
`pvr_read32p` → `pvr_map32` (masked into VRAM, `pvr_mem.cpp:212`/`:292`),
so a bad SOF wraps instead of crashing; no script in senkosp2dreamcast,
cleopatra or naomi2dreamcast references RAWFB or the old log text. Worst
case: a garbled PNG for a 0888 framebuffer with a non-640 stride — never a
crash, never a changed disc.
