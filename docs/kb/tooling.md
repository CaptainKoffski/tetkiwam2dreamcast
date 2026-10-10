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
    load Vulkan Portability library"). Stop by PID (`& pid=$!` …
    `kill $pid`), never `pkill -f`/`-x`: other projects run the same fork
    concurrently (2026-10-04).
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

## Free play tooling (2026-10-04)

- **Disassembly:** extract `1ST_READ.BIN` (first 1007472 B of track04.iso),
  then `/opt/toolchains/dc/sh-elf/bin/sh-elf-objdump -D -b binary -m sh4 -EL
  --adjust-vma=0x8c010000`. Literal-pool loads annotate the value
  (`! 904`), so `grep '! 904$'` finds every field access.
- **Scripted Start press (fork `core/ui/gui.cpp`, `gui_dumpFramebuffer`, added
  2026-10-04, fork commit `c52ea6987`):** `FLYCAST_START_AT=<frame>[,<frame>...]`
  holds controller-1 Start (`kcode[0]` bit `DC_BTN_START`) for frames
  [N, N+10). Each press logs `START_AT: Start down @N`. The maple poll reads
  global `kcode[]` (`core/network/ggpo.cpp` `getLocalInput`). Frame 1800 ≈ 35 s
  after launch on this disc (intro, just before the title). Presses 4 s apart
  (240 frames) step through intro → title → mode select.
- **Frame strip:** launch with `FLYCAST_SHOT=<dir>/cur.png FLYCAST_SHOT_EVERY=10`
  and copy `cur.png` every 2 s. `montage` (ImageMagick, Homebrew) tiles the
  copies. Two instances (stock + patched) can run side by side.

## CDI tooling (2026-10-05)

- **mkdcdisc v0.0.4** (`gitlab.com/simulant/mkdcdisc`, commit `2b98b0d`).
  Used from the sibling's build at
  `../senkosp2dreamcast/tools/mkdcdisc/build/mkdcdisc`; set `MKDCDISC=` to
  point elsewhere. Fresh install, per the sibling's `docs/kb/tooling.md`
  §Installs: `brew install meson ninja libisofs`, `git clone --depth 1
  https://gitlab.com/simulant/mkdcdisc.git && cd mkdcdisc && meson setup
  build && ninja -C build`. Facts this repo relies on: `-M` prints MSINFO
  (11702 for the default audio/data layout); `-b` scrambles an unscrambled
  binary; ISO level 2 + Rock Ridge (`src/iso_builder.cpp:90,95`), so the
  12.3 names like `TEEFFECTFILE.AFS` survive; the data track is padded to the
  disc's outer edge by default (`-N` turns that off), which is why the
  `.cdi` is 740 MB and zips to 45 MB.
- **Inspecting the image:** add `-I` to the mkdcdisc call to also dump
  the data track as `.iso`. The dump uses **relative** extents (root at LBA
  19), while the CDI's own PVD has absolute ones (root at 11721; find
  `\x01CD001\x01` in the .cdi). Use the CDI for absolute-LBA questions.
- **GD read trace:** `FLYCAST_CARTLOG=<file>` in the fork logs every drive
  transfer as `GDDMA fad=… secs=…` / `GDPIO …` (`core/hw/gdrom/gdromv3.cpp`
  `:136`/`:281`), and Flycast's own stdout logs `Sector Read miss FAD: N`.
  Compare the first reads after the boot file with the GDI's: the GDI's are
  `0xb06e` (45166, PVD), `0xb072`, ….
- **Read-parameter and SPI log (fork commit `851b823ba`, 2026-10-05..07):**
  `core/hw/gdrom/gdromv3.cpp` CD_READ adds a `GDREAD fad=… secs=… expdtype=N
  data= subh= head= other= prm=` cartlog line, GET_TOC adds `GDTOC area=N
  first=… t3=…`, and every SPI packet logs `GDSPI <12 bytes> sns= pc=`. Flycast doesn't act on `expdtype`, so this log is the only way
  to see the read mode the BIOS asks for. Rebuild: `cmake --build build -j8` in
  the fork.
- **Strict Flycast (SH4 cache model), 2026-10-05:** a separate tree in the fork,
  `build-strict/` (untracked):
  `cmake -S . -B build-strict -DCMAKE_BUILD_TYPE=Release
  -DCMAKE_OSX_ARCHITECTURES=arm64 -DUSE_BREAKPAD=OFF -DUSE_HOST_LIBZIP=ON
  -DZLIB_LIBRARY=/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/lib/libz.tbd
  "-DCMAKE_CXX_FLAGS=-DSTRICT_MODE -DTARGET_NO_REC" "-DCMAKE_C_FLAGS=-DSTRICT_MODE
  -DTARGET_NO_REC"`, then `cmake --build build-strict -j8`. Three traps:
  - `TARGET_NO_REC` is needed because the arm64 dynarec doesn't compile without
    FAST_MMU (`rec_arm64.cpp:1456` `mmuAddressLUT`).
  - `USE_BREAKPAD=OFF` is needed because `dump_syms` wants full Xcode.
  - The zlib path must be the `.tbd`; a bare `-lz` breaks the link.

  Run with `-config config:Dynarec.Enabled=no` (CLI only; `emu.cfg` stays `yes`).
  It's about 7–8× slower: the GDI reaches its WARNING screen at about 150 s.
  **Run one instance at a time:** three in parallel overheated the operator's
  laptop (2026-10-05).
- **Entry marker (diagnostic, not in the build):** `build/diag-r3/marker.py`
  `add_marker(boot)` (cdi.md §round 3 kit). Proof it executed: the fork's PVR
  log line `CLEO-SPG write VO_CONTROL = …08 … pc=8c105f70`. The white itself
  never shows in `FLYCAST_SHOT`, which only captures rendered frames.
- **Emulator leg:** the same launch as §Iplogo, with the `.cdi` as the disc.
  The fork boots CDIs on the real BIOS as-is. Gameplay leg:
  `FLYCAST_START_AT=1800,2100,…` (12 presses, 300 frames apart) + a
  `FLYCAST_SHOT` copy every 8 s up to 120 s gets into a 1P match.

## DreamShell tooling (2026-10-08..09)

- **DreamShell source:** `../senkosp2dreamcast/tools/dreamshell-4.0.4` matches the
  user's SD bundle (`~/Downloads/DreamShell_v4`, changelog "4.0.4.Release",
  `sd.bin` string "SD-SPI loader v0.8.4"). The same folder has
  `DreamShell_v4.0.4_Release.cdi` and `DS/EMU_DS_CORE.BIN`.
- **Fork instrumentation (fork commit `24b4dc256` in `../flycast4naomi2dreamcast`, 2026-10-10):**
  - **Emulated SD card** (`core/hw/sh4/modules/serial.cpp`, `namespace sdcard`).
    `FLYCAST_SDIMG=<raw MBR+FAT image>` attaches a read-only SDHC card to the SCIF
    pins as DreamShell's adapter wires them: RTS=/CS, CTS=CLK, TxD=MOSI, RxD=MISO,
    in SPI mode 0. It answers CMD0/8/55/41/58/59/16/9/10/13/17/18/12. With TE=1 it
    holds MOSI high, which models the transmitter owning the pin.
  - `FLYCAST_SDCYC=<n>` charges n extra cycles per `SCSPTR2` access. Measured:
    0 → about 2.7 MB/s, 14 → 487 KB/s, 55 → 140 KB/s.
  - cartlog `SDCMD` lines: every command except reads, plus read 1–3 and every
    500th, with emulated time and block count.
  - `SCIFWR` (SCIF register writes). `SCSPTR2`/`SCFTDR2` are capped at 300 lines;
    `SCSCR2`/`SCFCR2` at 5000.
  - `core/hw/mem/addrspace.cpp`:
    - `ISOLDRBANDLOW`: the lowest game-code store in `0x8c004000..0x8c010000`.
    - `PAGEFIRST`: the first store to each 4 KB RAM page once game code has run.
      Interpreter only.
  - `core/hw/gdrom/gdromv3.cpp` `GDDMADST`: GD DMA destination and length.
- **SD card image:** `mkfile -n 200m sd.img`, then
  `hdiutil attach -imagekey diskimage-class=CRawDiskImage -nomount sd.img`. Check
  that `diskutil info` says `Protocol: Disk Image` **before** running
  `diskutil partitionDisk <dev> MBR FAT32 SDCARD 100%`. Copy the GDI into
  `/TETRIS/`, then `hdiutil detach`. To make fragmented copies, interleave writes
  with a filler file. `fatfrag.py` (session scratch) counts fragments from the FAT.
- **DreamShell test disc:** copy `DS/`, then patch its `lua/startup.lua`: before
  `OpenApp(STARTUP_APP)`, open `minilzo`, `isofs` and `isoldr`, then
  `os.execute("isoldr -i -f /cd/TETRIS/tetris.gdi -d sd -P /cd/TETRIS/sdlike.cfg")`.
  `sdlike.cfg` holds `dma 0, async 8, irq 0, mode 0`, the same as the GUI's defaults.
  Put the GDI in `TETRIS/`, then run `mkdcdisc -b DS/EMU_DS_CORE.BIN -D <root>
  -o ds.cdi`.
  - Use `EMU_DS_CORE.BIN`: the normal core's SD probe misbehaves with nothing on
    the port.
  - Use a CDI, not `-F gdi`: DreamShell didn't find `/cd/DS` on the GDI build.
  - DreamShell itself is the same either way; only the game's reads go to the SD.
- **Strict build** (cache + MMU model, `build-strict/`, §CDI) is what reproduces
  the hang. Plain Flycast doesn't translate U0 addresses for DC games.
  - Rebuild with `cmake --build build-strict -j8`.
  - Run with `-config config:Dynarec.Enabled=no`, one instance at a time.
  - DreamShell → game attract takes about 3–5 min of wall time.
  - `EXC epc= evn=` lines are the exception tripwire.
- **Gotcha:** about one launch in three dies at startup with `Verify Failed:
  &mem_b[0] == … sq_buffer …` (`core/hw/sh4/dyna/driver.cpp:349`), before any
  guest code runs. Relaunch; the session's runner retries automatically.
