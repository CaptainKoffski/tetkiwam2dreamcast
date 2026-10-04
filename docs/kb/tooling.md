# Tooling

Recipes, citations and checksums. Narrative index: `00-status.md`.

## Base build (2026-10-03)

`python3 build_gdi.py` — chdman (`brew install rom-tools`, v0.289),
clang++, Python 3; inputs from `../naomi2dreamcast/naomi` (`NAOMI_DIR=`
to override). ~15 s on an M1. Reference sha1s in the README.

## Iplogo tooling (2026-10-04, branch `iplogo`)

- **iplogo.mr** — copied from `../senkosp2dreamcast/iplogo.mr`
  (operator-supplied there: dreamcast-talk forum file id 18794,
  Cloudflare-gated, browser download only). Repo root, gitignored
  (`/iplogo.mr`). Valid Sega MR: `MR` + 7×u32 LE at +2
  (size/0/dataoff/w/h/0/ncol) = 6807/—/0x11a/320/90/—/63; BGRA palette
  at +30, ncol×4; RLE data from dataoff.
- **MR slot facts + citations:** 0x3820 = makeip `src/mr.c:39`
  `MR_OFFSET` (+`:36` `MR_MAX_SIZE 8192`, `:436` memcpy), read from
  `../senkosp2dreamcast/tools/kos/utils/makeip/src/mr.c`; "Bootstrap 1
  (3800-5FFF) can be modified" = mc.pp.se/dc/ip.bin.html. Shipped IP.BIN
  cross-check: 8192-B zero run at track03 0x3820..0x5820; license code
  literal `0x8c00b820` at 0x083c.
- **MR decode (stdlib only):** RLE from makeip `gimp/file-mr.py`
  `mr_decode` — byte <0x80 literal; `0x81 n v` = run n of v; `0x82 n v`
  with n≥0x80 = run n−0x80+0x100; else `b v` = run b−0x80 of v. Decoded
  28800 px, hand-built PNG via zlib, viewed. ~25-line script, session
  scratchpad only — rebuild from this description if needed.
- **Control build:** `mv iplogo.mr iplogo.mr.aside; python3 build_gdi.py
  <scratch dir>; mv back` — the scratch track03 sha1 must equal the
  README's base-build value; byte-diff the two track03s and assert the
  differing range sits inside the slot.
- **Emulator capture (instrumented fork `../flycast4naomi2dreamcast`,
  real BIOS):**
  - Launch: `FLYCAST_SHOT_RAWFB=<png> [FLYCAST_SHOT=<png>
    FLYCAST_SHOT_EVERY=10] build/Flycast.app/Contents/MacOS/Flycast
    -config config:rend.vsync=no -config config:pvr.rend=0 <disc.gdi>`.
    Flags **before** the disc path (after it: "Rest of command line
    ignored"). `pvr.rend=0` is mandatory: `emu.cfg` has `pvr.rend = 4`
    (Vulkan) and the fork segfaults in `VulkanRenderer::Init` ("Failed to
    load Vulkan Portability library"). `pkill -9 -f
    "flycast4naomi2dreamcast.*Flycast"` between runs.
  - `$FLYCAST_SHOT` = last PVR-rendered frame; FB-only screens (BIOS
    license) come out as the background colour.
  - `$FLYCAST_SHOT_RAWFB` + `kill -USR2 <pid>` = guest scanout framebuffer
    at `FB_R_SOF1`, 640×480 linear, RGB565 or 0888 (0888 added here, fork
    commit `ab2196447`; other depths log "RAWFB: fb_depth not 565/0888"
    and skip, leaving the previous PNG in place — identical consecutive
    copies mean *skipped*, not *static*).
  - Timing from launch (this disc, M1): swirl ~7–11 s, license screen
    ~12–14 s, game framebuffer from ~15 s. A 0.5 s SIGUSR2 cadence from
    5 s catches it.
  - Fork rebuild: `cmake --build build -j"$(sysctl -n hw.ncpu)"` in the
    fork, ~4 s incremental for `gui.cpp`.
- **0.1.0 checksums (sha1):** tetris.gdi `1d6069f7…`, track01
  `5cf39417…`, track02 `6030e25d…`, track03
  **`736cbb18b0c39acc395a46b0692d8ae25dfa0e8f`** (base build:
  `d73e0903…`), track04 `5c18e14e…`. Full values in the README table.

## GDTEX tooling (2026-10-04)

- **0GDTEX.PVR** — operator-supplied cover art, repo root, gitignored
  (`/0GDTEX.PVR`). Accepted shape, asserted by `build_gdi.py`: bare
  `PVRT` + u32 size, byte 8 = 0x01 (RGB565), byte 9 = 0x09 (rectangle, raw
  scanlines), u16 LE 256×256 at +12/+14, pixels at +16, 131088 B total.
  The sibling's PNG → `sips` → `bmp2rgb565.py` path was not carried; feed a
  ready PVR (the sibling's `scripts/bmp2rgb565.py` + its `patch_gdtex`
  encode path is the recipe if a PNG is all there is).
- **Donor extent facts:** root-dir record found by searching the
  root-directory sector (LBA 45020) for `0GDTEX.PVR;1`, record starts 33
  bytes before the identifier, extent LBA at +2, size at +10 (LE). Here:
  LBA 81210, 131104 B, track03 offset 0x46b9000; header GBIX+PVRT, pixel
  format ARGB1555 (0x00), square twiddled (0x01), 256×256.
- **Twiddle:** `sp[v]` spreads 8 bits to even positions; offset =
  `(sp[y] | sp[x] << 1) * 2`. Source: Flycast `core/rend/texconv.cpp:37`
  `twiddle_slow`. Control: the donor's own twiddled art detwiddles to a
  clean picture with this order.
- **PVR decode to PNG (stdlib only):** RGB565 → `(r*255//31, g*255//63,
  b*255//31)`, ARGB1555 → 5-bit channels at 10/5/0; write an 8-bit RGB
  PNG with zlib + crc32. ~20-line script, session scratchpad only.
- **Checks to rerun after any change:** (1) byte-diff old/new track03 and
  assert every differing offset ∈ {extent+24} ∪ [extent+32, extent+32+
  131072); (2) detwiddle the on-disc payload and compare to input pixels;
  (3) control build with the file moved aside → track03 sha1 must equal
  the previous reference (`736cbb18…` as of 0.1.0).
- **0.2.0 checksums (sha1):** track03 with `iplogo.mr` + `0GDTEX.PVR`
  **`2157c4eeecd89c960eb8c22b167131cfd5833280`** (GDEMU-verified
  2026-10-04); gdi/track01/02/04 unchanged from 0.1.0.
