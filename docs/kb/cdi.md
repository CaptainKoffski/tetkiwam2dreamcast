# CDI for burned CD-Rs (2026-10-05)

**Ask:** `make release` should build a CDI next to the GDI, as in
senkosp2dreamcast (two zips, `[GDI] …` and `[CDI] …`).

**Approach:** unlike the sibling (whose shim streams a cart from a baked FAD
and needed a custom ISO), this game reads only ISO9660 files, so the CDI is
a file-level re-master. `make_cdi.py` reads `build/gdi`, so cover art, title
and free play carry over without being redone. It unpacks track03's tree
(base LBA 45000), takes `1ST_READ.BIN` from track04 (size from track03's
root record), patches it (below), and calls mkdcdisc once. mkdcdisc builds
the audio/data layout (session-2 data track at MSINFO 11702, `mkdcdisc -M`),
its own CD IP.BIN, and the scrambled boot file. That is the chain the sibling
proved on GDEMU after the retail GD IP.BIN killed real CD boots
(senkosp2dreamcast `docs/kb/tooling.md` §CDI mastering, hardware rounds 3–5).
IP fields copied from the GD IP: title, company `SEGA LC-T-00`, serial
`T0000M`, `V0.800`, `20021024`, peripherals `0799810`, plus `iplogo.mr` as
the license-screen logo. The area stays mkdcdisc's `JUE`, as in the sibling.
`__GAME__.BIN`/`__TEST__.BIN` (Naomi-header leftovers, also in the GDI) ship
untouched: no string in `1ST_READ.BIN` names them.

**Patch 1, LBA hack (CD only):** the game's Katana GDFS hardcodes the GD
high-density track. Words in `1ST_READ.BIN`, each the only one of its value:

| file off | used at | value | role |
|---|---|---|---|
| 0xc34 | 0x8c010b52 | 45150 | gdFsInit: HD TOC entry[2] must equal it, else return -51 (the mount carries on either way) |
| 0x12e8 | 0x8c01129c | 45150 | read path: `fad < 45150` → -32 |
| 0x16b4 | 0x8c0115ec | 45150 | second read path, same guard |
| 0xc5b10 | 0x8c010b62 | 45166 | PVD FAD gdFsInit reads |

All shift by `MSINFO − 45000` (−33298), the scene's binhack move. The TOC
check can't match on a CD: Flycast returns all-`0xFF` for an HD-area TOC on
non-GD media (fork `core/imgread/common.cpp:226`), so the emulator legs
below ran the −51 path, and the game ignores it.

**Patch 2, GD-only mount → CD read mode (CD only).** Two problems, one site:

- *Disc-type check.* With only patch 1 the game drew `----- Error -----
  vmsFileDeviceClass::setDirChashe`. The Flycast GDDMA trace showed why: after
  the boot file, its first filesystem read was **FAD 0**, where the GDI's is
  45166. gdFsInit compares the drive-status disc type with `0x80` (GD-ROM,
  literal at 0x8c010ad4) at `0x8c010aac..0x8c010ab9` and leaves before the
  mount on anything else.
- *Read mode (the GDEMU black screen, below).* The game never calls the GDROM
  sector-mode syscall (function 10, Katana `gdGdcChangeDataType`; its stub at
  `0x8c01c3dc` has no caller). After the game's drive init (CMD_INIT, `0x8c010528`)
  the real BIOS issues every CD_READ with expected data type **2**, as on the
  GDI, where the HD area is Mode 1. Its own boot reads of this CD use **4**,
  because mkdcdisc's data track is CD-ROM XA (Mode 2 Form 1; Flycast reports disc
  type `0x20`, fork `core/imgread/common.cpp:266`). Flycast ignores the field
  (CD_READ in `core/hw/gdrom/gdromv3.cpp` only acts on CD-DA/2340), so the
  emulator passed. Both primary sources set track type 2048 on XA media and
  1024 otherwise: KOS `kernel/arch/dreamcast/hardware/cdrom.c`
  `cdrom_change_datatype`, which always runs after its CMD_INIT, and DreamShell
  isoldr `firmware/isoldr/syscalls/syscallsc.c:89` `gdGdcChangeDataType`.

Fix: the check's 14 bytes become `mov.l @(0x8c010ad4),r1; jsr @r1; nop ×5`.
The check's `0x0080` literal word becomes the helper's address. The helper
sits at `0x8c01c3f0`, over two MISC syscall stubs (r6=−1, functions 0/1) that
nothing references: `mova params,r0; bra 0x8c01c3dc` (the function-10 stub)
`; mov r0,r4` in the delay slot. params at `0x8c01c408` = `{0 (set), 0x2000
(data area), 2048, 2048}`, KOS's XA values. r0–r7 are dead at the site (the
fall-through at `0x8c010aba` reloads all it uses). No load or branch anywhere
in `1ST_READ.BIN` targets these bytes, including via P2/physical aliases
(scanned 2026-10-05). The disassembly was checked after patching.
`make_cdi.py` asserts the original bytes and that the file length is unchanged.

**Checks (2026-10-05), instrumented Flycast + real BIOS:**
- `cdi-hack` (patch 1 only): boots through BIOS + license, then the
  setDirChashe error screen, waiting on "continues by start". So the leg
  can fail, and it found the missing patch.
- `cdi2`/`cdi3` (patch 1 + the disc-type check only, `cmp/eq r3,r3`):
  copyright screen with PRESS START / FREE PLAY, then play-style select, then 1P
  into a live match. 554 GD reads, 0 `Sector Read miss`, PVD at FAD 11868, files
  read from the outer edge (FAD ≈ 0x47xxx–0x4exxx, mkdcdisc's data-track
  padding). **This build failed on GDEMU** (below).
- `cdi-rd` (same build, fork GDREAD log): BIOS boot reads `expdtype=4`, all
  game reads `expdtype=2`. `gdi-rd` (GDI control): everything `expdtype=2`.
- `cdi4` (current patch 2): **145/145 reads `expdtype=4`**, BIOS and game
  alike. 554 GD transfers, 0 misses, 0 resets, title → play-style select → 1P
  match (timer 0:05 → 0:29). One false start on the way: the first patch
  packed 36 bytes into a 40-byte bytearray slice, which shrank `1ST_READ.BIN` by
  4 bytes and caused a reset loop right after boot (`cdi5`, an interpreter leg
  with `FLYCAST_ENTRYPC=8c010aac`, never reached the site). Hence the length
  assert.
- GDI unchanged: `make verify` OK after `make release`.
- Not byte-reproducible, like the sibling's CDI: two builds differ in 1,740
  bytes in the PVD/directory sectors (timestamps, plus those sectors'
  EDC/ECC) and 128 bytes in the CDI footer. No file data differs. So there's
  no CDI row in `make verify`.

**Hardware round 1 (2026-10-05, GDEMU, user report): FAIL.** "Just black
screen after the Sega TM logo, no game shown at all (I waited a long)". Build:
patch 1 + `cmp/eq r3,r3`. IP.BIN ran (TM screen drawn). A black screen
can't tell a failed boot-file load from a game that started and then hung. In
the emulator the game's first visible frame comes after its first filesystem
reads, so a Mode 1 read of a Mode 2 Form 1 track, refused by the drive GDEMU
emulates, would look exactly like this. That's the read-mode fix
above. The hypothesis is consistent but unproven until round 2.

**Hardware round 2 (2026-10-05, GDEMU, user report): FAIL, same symptom.**
"I see the SEGA TM splash, and then black screen, no sound, no image, nothing."
Build: patch 1 + read-mode patch 2 (sha1 `787f3be0…`). So read mode is not the
whole story, maybe not part of it at all. Patch 2 stays: the BIOS must not read
an XA track as Mode 1, whatever else is wrong.

**Investigation after round 2: cache state, ruled out in emulation.** The one
clear IP.BIN difference that Flycast's normal build can't see:
- Katana's bootstrap 2 enters the game with the caches **off**: `CCR = 0`
  (`0x8c00e0d0`), then an ICI invalidate (`0x8c00e0dc`), then SR `0x700000f0`,
  r15/VBR `0x8c00f400`, FPSCR `0x40000`, and `jsr` to the game from P2
  (`0xac00e0ae`).
- mkdcdisc's bootstrap writes `CCR = 0x090b` (ICE|OCE|WT, plus both
  invalidates; `0x8c00e00a`, literal word at IP offset 0x6054), then returns to
  the BIOS, which enters the game.
- The game's first block (`0x8c01000c`) does a read-modify-write of CCR from P1
  code.

Flycast models the SH4 caches only in a `STRICT_MODE` interpreter build
(`core/hw/sh4/sh4_mem.cpp:307`). With one built (tooling.md §Strict Flycast),
three legs all reached the game's own WARNING screen after the same 30 reads:
the GDI (Katana IP), the round-2 CDI (caches on), and V1, the round-2 CDI with
mkdcdisc's CCR word changed to `0x0808` (caches off, both invalidates kept). The
hang doesn't reproduce, so V1 isn't shipped. Caveat: this only rules it out as
far as Flycast's cache model is faithful.

**Hardware round 3 kit (2026-10-05): entry marker, built in `build/diag-r3/`.**
Two theories that fit the emulator failed on hardware, so the next step is
evidence from the console. `marker.py` patches the game's entry (6 NOPs at
`0x8c010000`) to jump to 64 bytes appended past the file end, which crt0's BSS
clear later overwrites. Those bytes set the border white and blank the video
(VO_CONTROL bit 3, so the whole screen shows the border: Flycast
`core/rend/gles/gldraw.cpp:672,776`), wait 120 vsyncs (SPG_STATUS bit 13,
`core/hw/pvr/pvr_regs.h:205`), and continue into crt0. The game's own video
init unblanks later (`pc=8c023bc0`). Flycast: the white is held 2.16 s (GDI) /
2.14 s (CDI) between the marker's blank and the game's unblank (PVR log), and
both reach attract.
- **A** `A-gdi-marker/`: the 0.4.0 GDI plus the marker (track04 sha1
  `38ce9f9c…`; the root-dir size of `1ST_READ.BIN` is updated). Control: it must
  show TM → about 2 s white → the game, which proves the marker is visible on
  the operator's display.
- **B** `B-cdi-marker/tetris.cdi`: the round-2 CDI plus the marker (sha1
  `97a4715d…`). Read it as: black after TM = the game never started
  (boot/IP); white that stays = it started and hung before video init; white
  for about 2 s, then black = it hung later.

**Hardware round 3 verdict (2026-10-07, GDEMU, user report):** "A shows white
then game; B shows white then black, no game." So the marker is visible on the
operator's display, and **on the CDI the game starts**: entry reached, and
something rewrote the video registers after the 2 s hold, most likely the game's
own video init (`pc=8c023bc0` in Flycast). IP.BIN, the boot-file load and the
scramble are all exonerated. The hang comes after video init, which in Flycast
is when drive traffic starts (first FS read about 44 ms after the unblank).

**Round 4 kit (2026-10-07): serial GD-syscall tracer, `build/diag-r4/`.**
`tools/diag/gdtrace.c` is C built with the sh-elf toolchain and linked at
`0x8c004000` (dcload-serial's spot, `target-src/dcload/dcload.x:13`; zero in the
menu-time RAM dump). `tools/diag/mkdiag.py` builds it:
- The game's entry jumps to a 64-byte loader past the end of `1ST_READ.BIN`. The
  loader copies the tracer to `0xac004000`, calls `gdtrace_init` (SCIF 115200
  8N1, the KOS `scif_init` sequence) and enters crt0.
- The 11 GD syscall stubs (`0x8c01c314 + 0x14·func`) get their vector literal
  (`0x8c0000bc`, at stub+0x10) re-pointed to `hook_vec`.

Each call is passed through unchanged and logged: SEND_COMMAND with params and
handle, CHECK_COMMAND status transitions (`st` = error words), DRIVE_STATUS on
change, sector mode, other functions on change, and a heartbeat (`HB`) every
20,000 calls. The tracer has no MAC, mul/div or FPU instructions: the game is
Hitachi-ABI code, and the objdump hits are all literal pools and strings.
Flycast with `Debug.SerialConsoleEnabled=yes`:
- A (GDI): status `1/0x80` (GD-ROM), GET_VERSION (`0x28`), GETTOC2 (`0x13`), DMA
  reads from FAD `0xb06e`.
- B (CDI): status `1/0x20`, `MODE 0 2000 800 800`, GETTOC2 fails (`-1`, `st 5`;
  no HD area on a CD), then reads from FAD `0x2e5c`.

Both reach attract. Capture: `tools/diag/capture_serial.sh <leg>`, adapted
from the sibling.

**Hardware round 4 verdict (2026-10-07, GDEMU + coder's cable, tracer v1):**
logs in `build/diag-r4/r4-gdi.log` and `r4-cdi.log`. Bonus: the game prints
its own banner over SCIF ("Nindows2 for DREAMCAST version 2.12 … Startup SCIF
115200 BPS", heap at `$8cdf4ac0`). Both discs are identical up to the game's
drive re-init: GDROM_INIT (syscall 3), then `SEND cmd 0x18` (CD_CMD_INIT, KOS
`include/dc/syscalls.h:264`).
- **GDI:** `CHK -> 1 … ata 1`, then `-> 2` (`size 0x198`, disc `0x80`), then the
  reads.
- **CDI:** `CHK -> 1 st 0 0 0 3` **forever**, with about 6.3 M further syscalls
  of polling and no read ever sent. That last word is the BIOS's ATA status
  (`include/dc/syscalls.h:454-474`): 1 = `ATA_STAT_IRQ`, waiting for the drive's
  interrupt; 3 = `ATA_STAT_DRQ_1`, inside a data transfer.

**So on GDEMU + CDI, the BIOS's CMD_INIT stalls in a data phase.** The fork's new
`GDSPI` log (every SPI packet, `gdromv3.cpp` `gd_process_spi_cmd`) shows what
CMD_INIT sends on Flycast: `00` TEST_UNIT, `11 00 12 00 08` REQ_MODE (data in),
`70 1f` SYS_CHK_SECU, `71 1f` SYS_REQ_SECU (data in), `14 00 00 01 98` GET_TOC
(data in, `0x198` = the INIT `size`). The BIOS runs the same sequence twice at
boot, and that works on the console, so the trigger is the conditions by the
time the game sends it, not the packets themselves. Still open: which of the
three data-in phases stalls.

**Round 5 kit C/D (2026-10-07): superseded before it ran.** C was tracer v2
(register dump when a command stalls), D sent the game's CMD_INIT as a NOP.
Both played in Flycast. Both were retired by the next finding, which explains
the stall instead of probing it.

## Existing GDI→CDI tools, and the G1 bus unlock (2026-10-07)

**Survey.** The scene's GD-rip→CD-R tools are all one recipe from about 2001:
extract the files; run Echelon's `binhack` (one LBA word in `1ST_READ.BIN`
plus a hacked IP.BIN, `IP.HAK`); `mkisofs -C 0,MSINFO`; then `cdi4dc`.
- BootDreams, lazyboot and mkcdi (Conkwer, GPLv3, Windows-first; lazyboot
  `b75e560`) and DreamcastCdiTool wrap that chain.
- binhack32 (FamilyGuy, GPLv3, sourceforge `binhack32` git `79902aa`) is the
  clone of `binhack` with source.
- Our chain is the same recipe, with mkdcdisc doing mkisofs + cdi4dc +
  scramble + IP.

**binhack's boot-file hack wouldn't do this game on its own.** It patches only
the word 8 bytes before the GDFS's `"CD001"` string to MSINFO + 166 (binhack32
`src/main.cpp`, `binhack.cpp` `searchHackOffset`). That word is our 0xc5b10. It
doesn't touch the three 45150 words, and two of them are the read paths'
`fad < 45150 → -32` guards (patch 1 table), so every CD read would fail.

**`IP.HAK` is the useful part.** binhack writes 11500 bytes of bootstrap over
IP.BIN `0x3704..0x63ef` (`binhack.hpp` `bootsector_hack_data`). Disassembled
(IP at 0x8c008000, our GD IP as the base), the code at `0x8c00e1a0` does:
1. **G1 bus unlock:** `0x1fffff → 0xa05f74e4`, then reads all 0x80000 BIOS
   words at `0xa0000000`.
2. Two in-RAM BIOS patches (search 0xac000000–0xac003ff9, 10-byte pattern →
   replacement). Both patterns are in the BIOS dump (sha256 `88d6a666…`, ROM
   offsets 0x31d6 and 0x3602):
   - 0x31d6: the drive-status code keeps `status & 15`, and the disc type
     becomes `| 0x80` (GD-ROM). This is our patch 2's disc-check removal, done
     in the BIOS.
   - 0x3602: a parameter word `0x2400 → 0x2800`. That looks like data area
     0x2000 | Mode 1 0x400 → | XA 0x800 (KOS's values), i.e. our patch 2's
     sector-mode call, done in the BIOS.
3. GDROM INIT (syscall 3), then CMD_INIT (24) polled to completion.
4. A scramble pass over `1ST_READ.BIN` in RAM (the KOS scramble LCG
   0x83d/0x2439, size at IP 0x639c). The boot ROM descrambles on CD boot and
   binhack leaves the file plain, so this restores it.
5. `jmp 0xac010000`.

We already had (2) as patch 2 and (4) via mkdcdisc `-b`. **We lacked (1).**

**What the unlock is (primary sources):**
- KOS `cdrom_init` does it whenever the protection status (`0x5f74ec`) isn't
  "passed": `kernel/arch/dreamcast/hardware/cdrom.c:781-797`, register names in
  `include/dc/g1ata.h:121-143` (senkosp2dreamcast `tools/kos` `705c8629`). So
  every homebrew CDI unlocks the bus itself, senko's included.
- The boot ROM writes 0x1fffff there at reset and then copies itself out
  (`0xa000034a`).
- The boot ROM also has a routine that writes `0x42fe` with no read
  (`0xa0004ae8`, called at the end of the GD-command routine at `0xa0004af0`).
  Which boot path runs it isn't traced yet.
- Flycast logs the register and does nothing else (`core/hw/holly/sb.cpp:204-209`;
  its comment lists 0x42fe as a known value), so no emulator leg could ever show
  a locked bus.
- Our stall fits a locked bus: the game's first data-in command waits in DRQ
  forever, and the same command on the GD boot completes.

**Patch 3 (CD only, `make_cdi.py`).** The entry's 6 nops become `mov.l; jmp` to
a 40-byte stub appended past the end of the file. The stub is binhack's loop
instruction for instruction: `0x1fffff → 0xa05f74e4`, read 0x80000 words from
`0xa0000000`, `jmp 0x8c01000c`. The stub sits in BSS that crt0 clears afterwards;
the round-4 tracer loader used the same mechanism on hardware. KOS's `0xe6ff`
custom-BIOS branch (1 KB read) is left out. `tools/diag/mkdiag.py`'s tracer now
chains: tracer loader → unlock stub → crt0.

Flycast (fork, real BIOS, one instance):
- `build/cdi/tetris.cdi`: attract, FREE PLAY, 33 reads in 40 s.
- `F-cdi-unlock-trace`: tracer banner, game banner, `SEND cmd 0x18` → reads,
  33 reads in 35 s.

That proves the stub runs and returns, not that it unlocks anything.

**Round 5 (2026-10-07):**
- **E** = `build/cdi/tetris.cdi`, the exact release CDI.
- **F** = `build/diag-r5/F-cdi-unlock-trace/tetris.cdi`, the same plus tracer v2,
  captured to `build/diag-r5/r5-f.log`. Only needed if E is black.

**Hardware round 5 verdict (2026-10-07, GDEMU): E PASSES.** User report: "E works,
game shows up on GDEMU", then "I actually played a bit". Shipped as 0.5.0. The same disc and console showed a black screen in
rounds 1–4. The only change since round 4 is patch 3, so the locked G1 bus was
the round-4 stall. F wasn't run. `make release` rebuilt the CDI afterwards
(sha256 `303546…` vs tested `35375c…`). The two differ only in sectors 16–31 of the
data track (volume descriptors and directory records): the ISO date fields
(PVD +178/179, +823…; record +22/23) and the EDC/ECC over them. File
contents are byte-identical.

**Owed:** a real CD-R burn on a MIL-CD-capable console (GDEMU emulates the
drive, not the laser).
