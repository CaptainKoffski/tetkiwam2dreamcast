# DreamShell ISO Loader from an SD card on the serial port (2026-10-08..09)

**Report (user, 2026-10-08):** "The game does not work via serial (DreamShell)",
then "black screen on default settings of iso loader".

**Rig:**
- DreamShell 4.0.4 itself is launched from GDEMU. The game GDI sits on an SD card
  on the serial port, run from ISO Loader with **default settings**.
- isoldr firmware `sd.bin` v0.8.4 ("DreamShell ISO from SD-SPI loader v0.8.4").
- VGA cable. Other games boot from ISO Loader with defaults on the same card.

Sources:
- DreamShell 4.0.4: `../senkosp2dreamcast/tools/dreamshell-4.0.4`, the same
  version as the user's `~/Downloads/DreamShell_v4`.
- DreamShell HEAD: `../senkosp2dreamcast/tools/dreamshell-src`, at `9b59b44`.

## Root cause: the game turns the MMU on, and isoldr's SD path writes through it

1. **The game enables the SH4 MMU.** `0x8c015830` writes `MMUCR = 0x00040005`
   (AT=1, TI, URB=1), called from the init at `0x8c016da6`. Every leg logs it
   (fork `MMUCRWR ... pc=8c015838`). The UTLB is used to map the store queues
   (`0x8c015838` fills UTLB entries; `0x8c015a3c`/`0x8c015a5c` convert RAM/VRAM
   addresses to `0xe0000000`/`0xe1000000` SQ addresses). So simply turning the MMU
   off would break the game's SQ transfers.
2. **Its GD reads pass physical DMA buffers.** The Katana gdc read request at
   `0x8c01032a`:
   - DMA (cmd 17): `params[2] = buf & 0x1fffffff`, using the literal at
     `0x8c010508`, so `0x0c…`.
   - PIO (cmd 16): `params[2] = (buf & 0x1fffffff) | 0xa0000000`, so P2.

   The round-4 trace confirms it (`SEND cmd 00000011 … 0c1876a0`).
3. **isoldr's SD firmware copies DMA reads with the CPU.**
   - DMA is off for SD (`modules/isoldr/preset.c:221` `isoldr_can_use_dma`).
   - The "pseudo-async" read (`firmware/isoldr/loader/syscalls.c` `data_transfer`)
     writes the sectors to `(uint8 *)params[2]`.
   - The store is `mov.b r1,@r3` at `0x8c008376` in `spi_rec_data`, with the
     loader at `0x8c004400` after its 1 KB params block.

   With the MMU on, `0x0c…` is a translated U0 address with no TLB entry, so the
   store takes a data TLB miss (EXPEVT `0x060`). It goes through the **game's**
   VBR (`0x8c00f400` → `0x8c00f800`) into its crash handler (`0x8c014xxx`, the
   "Syint" register dump), and the console sits on a black screen with no sound.
   Real GD DMA never goes through the MMU, which is why GDEMU works. isoldr 4.0.4
   has `mmu_disable()`/`mmu_restore()` (`loader/mmu.c`) but never calls them. HEAD
   only special-cases the CD filesystem (`fs/cd/cdfs.c:322`).

**Fix (`build_gdi.py`, both discs):**
- Change the mask literal at `0x8c010508` from `0x1fffffff` to `0xffffffff`: file
  offset `0x50b`, `0x1f` → `0xff`, with the original 4 bytes asserted. That literal
  has exactly one user (`0x8c01033c`).
- DMA reads now pass the caller's P1 address (`0x8c…`, never MMU-translated).
  isoldr writes it through the cache and purges (`dcache_purge_range`).
- PIO reads still OR in `0xa0000000` (unchanged).
- Real DMA: Holly keeps only bits 28:5 of `SB_GDSTAR`
  (`setRW<SB_GDSTAR_addr, u32, 0x1fffffe0>`, Flycast `core/hw/holly/sb.cpp:385`).
  So a P1 address lands at the same physical RAM. The real BIOS code accepts it:
  Flycast runs `dc_boot.bin` as LLE, and the GDI/CDI legs below play.
- GDI track04 sha1 `27bc2a196964a9f131dec3229099f14118ee7e4e`. It differs from
  0.5.0 in that one byte; track01–03 and `.gdi` are unchanged.

## Round 1 (2026-10-08): serial console off. Wrong cause, hardware still black

The first theory was the SCIF conflict. isoldr bit-bangs the SD card through
`SCSPTR2`: RTS=/CS, CTS=CLK, TxD=DIN, RxD=DOUT (`dev/sd/spi.c:8-16`). The game's
Nindows2 debug console enables the transmitter (`SCSCR2 = 0x70` at
`0x8c07483e`), gated on bit 2 of a config word that the game sets to 7 at
`0x8c083f10`. Round 1 shipped `7` → `3` (track04 `0392c50b…`). **User: "still
black."** The emulated SD card below shows why it was never the cause.
isoldr re-runs `spi_init` (`SCSCR2 = 0`, `pc=8c004a76`) when the game calls
GDROM_INIT. That happens *after* the game's SCIF setup and before any SD read
(`sd_stock2`). So the transmitter is off again before it matters. The serial patch
was dropped from the build.

Also measured and ruled out on the way:
- **isoldr default placement** (`0x8c004000`): game code never writes below
  `0x8c00c000`, where crt0 fills the stack region with `"SEGA"`. The `sd`
  loader's own `loader_size` word gives loader_end `0x8c00b8b0` and heap base
  `0x8c00b8c0`, which leaves 1,856 B.
- **Track file fragmentation** (fast-seek link maps grow the heap): 50- and
  400-fragment `track03.iso` cards both play.
- **SD speed**: the emulated card throttled to 487 KB/s and 140 KB/s plays.

## Emulator legs (instrumented Flycast fork, real BIOS; recipe: `tooling.md` §DreamShell)

DreamShell `EMU_DS_CORE.BIN` + `DS/` + the GDI, mastered by mkdcdisc into a CDI.
Its `lua/startup.lua` runs `isoldr -i -f /cd/TETRIS/tetris.gdi -d sd` with
`dma 0, async 8, irq 0`. Those are the GUI's defaults, since the GUI also calls
`isoldr_apply_preset(info, NULL)` (`applications/iso_loader/modules/module.c:1996`).
The fork's emulated SD card serves a FAT32 image holding the same GDI.

| leg | Flycast | game build | result |
|---|---|---|---|
| `ds3` | normal | serial-off | plays (isoldr `cd` firmware, not SD) |
| `sd1` | normal | serial-off | plays |
| `sd_stock2` | normal | 0.5.0 | plays; game SCIF on, then isoldr `spi_init` before any read |
| `frag50`/`frag400` | normal | serial-off | plays |
| `cyc14`/`cyc55` | normal | serial-off, 487 / 140 KB/s | plays |
| `strict1` | cache/MMU | serial-off | **TLB-miss loop at `0x8c008376`, game never shows** |
| `strict_p1` | cache/MMU | serial-off + P1 DMA | plays to attract, 0 exceptions |
| `strict_fin` | cache/MMU | shipped (P1 DMA only, track04 `27bc2a19…`) | MMU on under isoldr (`MMUCR=00040005`, `vecbc=8c009d6e`), 0 exceptions, WARNING → SUCCESS → title |

Regression, real BIOS with no DreamShell (`fin_gdi`, `fin_cdi`): both play into a
1P match, with 457 GD DMA transfers like the stock leg. The CDI keeps 107/107
reads `expdtype=4`.

## Hardware round 2 (2026-10-10): PASS

Kit: `build/gdi/` from this build (track04 `27bc2a19…`), copied to the DreamShell SD
card and launched from ISO Loader with **default settings**. User report:
"works on DreamShell now." Shipped as 0.6.0. GDEMU regression on this build
hasn't been reported. By construction the GDI differs from 0.5.0 only in the
DMA mask byte, and the real-BIOS GDI/CDI legs above play.
