# GDTEX — cover art in the BIOS / GDEMU disc menu (2026-10-04)

**Funding:** operator, 2026-10-04: "0GDTEX.PVR is the game cover texture,
replace the existing one with it, just as we did in senkosp2dreamcast".
Sibling reference: senkosp2dreamcast `scripts/make_gdi.py` `patch_gdtex`
(Task #28, `phase5-hardware.md` §"0GDTEX disc art incorporated"; art seen
in the GDEMU menu there).

## Recon

- **Input** (`0GDTEX.PVR`, repo root, 131088 B, md5 `8714ad11…`; a
  different picture from the sibling's `0GDTEX.pvr`): bare `PVRT`, data
  size 0x20008, attrs `01 09` = RGB565 / rectangle (raw scanline order),
  256×256, pixels at +16. Decoded to PNG (stdlib, scratchpad) and viewed:
  Tetris Kiwamemichi cover — TETRIS logo, NAOMI GD-ROM SYSTEM mark,
  SUCCESS, Dreamcast swirl; right side up, colours sane.
- **Donor extent** (root-dir record, identifier at track03 0xa065, record
  = identifier − 33): LBA 81210, 131104 B = 32-byte header + 65536×2
  pixels, track03 offset 0x46b9000. Header
  `GBIX 08 00 00 00 | 00×8 | PVRT 08 00 02 00 | 00 01 00 00 | 00 01 00 01`
  → pixel format **0x00 = ARGB1555**, data format 0x01 = square twiddled,
  256×256. **Differs from the sibling's donor** (Dolphin Blue: `01 01`,
  RGB565, GBIX index 1): keeping the header verbatim, as the sibling does,
  would label RGB565 pixels ARGB1555 here, so the pixel-format byte has to
  follow the input.
- **What the donor art is:** detwiddled (Morton, y bits even / x bits odd)
  and decoded as ARGB1555 → a clean picture of a CD labelled ぽけかの
  (*Pokekano*, Success) with three chibi characters. A Success/Sega
  leftover, not Tetris. Doubles as the **twiddle-order control**: a
  Sega-authored twiddled PVR from this very disc comes out unscrambled with
  the same bit order the build writes.
- **Citations:** twiddle order = Flycast `core/rend/texconv.cpp:37`
  `twiddle_slow` (y bit placed at shift 0, then x: y in even bit positions,
  x in odd; copy at `../flycast4naomi2dreamcast`). Pixel-format codes = KOS
  `utils/pvrtex/pvr_texture.h:41-42` enum order `PT_ARGB1555` = 0,
  `PT_RGB565` = 1 (copy at `../senkosp2dreamcast/tools/kos/`). Data-format
  bytes 0x01 square-twiddled / 0x09 rectangle as asserted by the sibling's
  hardware-verified `patch_gdtex`. RGB565 square-twiddled 256×256 behind
  GBIX is exactly what the sibling's donor shipped and what its replacement
  renders on real hardware, so the format flip is hardware-proven safe.

## Fix — inline in build_gdi.py

`iso` is already a bytearray: find `0GDTEX.PVR;1` inside the
root-directory sector, read extent LBA + size from the record, assert the
donor shape (GBIX+PVRT, square-twiddled, 256×256, 131104 B) and the input
shape (PVRT, RGB565 rectangle, 256×256, 131088 B), twiddle the 65536
pixels into the extent payload in place, set header byte +24 to 1
(RGB565). GBIX and every other header byte stay the donor's; directory
records and layout untouched. Absent file → nothing written. Gitignored
`/0GDTEX.PVR` (cover art is copyrighted; same rule as `iplogo.mr`).

## Verification (offline, 2026-10-04)

- **Delta confinement:** 120079 bytes differ between the 0.1.0 track03
  (`736cbb18…`) and the new one, range 0x46b9018..0x46d901f; every one is
  either the pixel-format byte (extent+24) or inside the 131072-byte
  payload (extent+32..). Header after:
  `GBIX 08 00 00 00 | 00×8 | PVRT 08 00 02 00 | 01 01 00 00 | 00 01 00 01`.
- **Round trip:** detwiddling the on-disc payload == input pixels, byte
  exact.
- **Control build (working-style rule 2):** `0GDTEX.PVR` moved aside,
  rebuilt to scratch: track03 sha1
  `736cbb18b0c39acc395a46b0692d8ae25dfa0e8f` = 0.1.0 exactly. tetris.gdi,
  track01/02/04 sha1-identical either way.
- **Candidate:** track03 sha1 `2157c4eeecd89c960eb8c22b167131cfd5833280`
  (with `iplogo.mr` + `0GDTEX.PVR`); everything else unchanged.
- **Not done:** an emulator view of the BIOS disc menu. The real BIOS
  autoboots a bootable GD, and the instrumented fork has no headless
  disc-insert hook (`DiscSwap` is reachable from the GUI/Lua only), so
  getting the menu up with the disc in would mean fork work for a proxy
  result. The sibling banked the same step on the GDEMU menu alone.

## Hardware verdict (2026-10-04) — PASS; GDTEX CLOSED, release 0.2.0

**Operator:** "Work perfectly on the HW". One-round close, same day.
Committed on `main` with annotated tag `0.2.0`, both pushed. Rebuild
note: `iplogo.mr` **and** `0GDTEX.PVR` must be at repo root to reproduce
the 0.2.0 track03 (`2157c4ee…`); without the art file the build returns
the 0.1.0 track03 by design.
