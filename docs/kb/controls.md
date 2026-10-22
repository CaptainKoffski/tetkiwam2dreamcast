# Controls and arcade sticks (2026-10-10)

**Asks:** (1) does this game have senkosp2dreamcast's arcade-stick bug, where
shield + OverDrive were stuck held from boot (`../senkosp2dreamcast/docs/kb/input-map.md`
§Non-standard controllers)? (2) Is it playable on an arcade stick, which has
A/B/C/X/Y/Z and no triggers?

**Answers (emulator only):** (1) no stuck input on Flycast's Arcade Stick. (2) yes:
every gameplay action is on the stick. The R trigger only duplicates HOLD, which
is also on Y. No real arcade stick has been tried on hardware.

## Why senkosp's bug can't happen the same way here

senkosp's jam was in its own shim (`jvs.c`), which read the trigger bytes of a
device with no triggers as half-pressed. Tetris has no shim: `1ST_READ.BIN`
reads pads through Sega's own library (strings `pd Ver 2.02 Build:Mar 09 2000`,
`Shinobi Ver 2.25`).

Flycast's Arcade Stick (`MDT_AsciiStick = 4`, `core/hw/maple/maple_cfg.h`;
CLI `-config input:device1=4`) declares no analog axes (DEVINFO `0xff070000`)
but sends `0x80` in all six axis bytes (`core/hw/maple/maple_devs.cpp`
`maple_ascii_stick`). Every GetCondition reply writes all six bytes, whatever
the device declares (the condition handler's `for (axis < 6) w8(getAnalogAxis())`).
Its button word passes C and Z (`kcode | 0xF800`); the standard pad masks them
(`| 0xF901`). The real HKT-7300's filler is undocumented.

## Stuck-input legs

Flycast fork, real BIOS, release GDI. The same scripted Start schedule reaches a
1P match, and each leg takes 33 shots named by frame number (every 240 frames,
240–7920). Each shot is compared pixel for pixel with the standard-pad leg. Recipe
and hooks: `tooling.md` §Controls tooling.

| leg | device | extra input | vs pad leg |
|---|---|---|---|
| pad again | pad | — | identical 33/33 (repeatability: the setup is deterministic) |
| **stick** | Arcade Stick, `0x80` filler | — | **identical 33/33: no stuck input** |
| trig80 | pad | L + R held at `0x80` all run | identical 33/33 |
| trigff | pad | L + R held fully (`0xFF`) all run | differs from frame 4800 (match start) on |
| stickff | Arcade Stick, filler forced to `0xFF` | — | identical 33/33 |

trigff shows the legs catch a held trigger. trig80 shows `0x80` isn't a press for
this game. stickff vs trigff decides it: the same `0xFF` trigger bytes change the
game from a pad and are ignored from the stick. So the pd library ignores axes
the device doesn't declare, which is the gate senkosp had to add by hand
(`probe_devinfo()`/`dc_cond_to_pressed()`). Whatever filler a real stick sends
shouldn't matter, as long as it declares no triggers the way Flycast's model does.

Wall-clock frame copies are not good enough for this: an earlier trig80 run copied
`cur.png` every 4 s and appeared to differ, but the BIOS boot frames already
differed (launch timing). Frame-numbered shots removed that.

## Button map

Same setup. Each leg presses one input for 10 frames at frame 5400 (the first
piece, an I, falling) and at 6300 (the second, a Z), then compares shots 5520,
5760, 6480 and 6720 with the no-press leg. In all 10 legs every shot before the
first press is identical to the no-press leg.

| input | in a match | on the arcade stick |
|---|---|---|
| lever left | moves the piece one column | ✅ |
| lever up | hard drop (score appears) | ✅ |
| A | rotate | ✅ |
| B | rotate the other way (from the same spot, A and B leave the I and the Z one column apart) | ✅ |
| Y | HOLD (the falling piece goes to the HOLD box) | ✅ |
| R trigger (pad) | HOLD, pixel-identical to the Y leg | — (Y does it) |
| X, L trigger, Z | nothing: identical to the no-press leg | — |
| C | nothing in this build; HOLD since the 2026-10-11 patch (§HOLD on C) | ✅ (since the patch) |
| Start | title and menus (every leg reached the match on Start alone) | ✅ |

So on the stick: rotate with A and B (bottom row), hold with Y (top row),
move and drop with the lever. X, C and Z do nothing. (Since §HOLD on C, C holds too.)

**Not checked:** lever down and right (they're the same D-pad bits as the pad's,
so presumably soft drop and move right); which way A and B turn; menu buttons
other than Start; the Naomi original's button layout; and any real arcade stick
on hardware. The remaining hardware question is whether a real HKT-7300 declares
no analog axes the way Flycast's model does.

## HOLD on C (2026-10-11)

**Ask:** put HOLD on C as well, so a stick has it on the bottom row next to A/B.

**Where the game reads buttons.** Sega's pd library keeps one 52-byte record per
port at `0x8c10615c + port × 52` (`pdGetPeripheral`, `0x8c0134be`): `support` at
+4, `on`/`off`/`press`/`release` at +8/+12/+16/+20, the previous `on` at +44.
Its bits follow the maple button word (C 0, B 1, A 2, Start 3, D-pad 4–7, Z 8,
Y 9, X 10), with the digital triggers at R 16 / L 17. The digital triggers come from
the analog bytes with press/release thresholds `0xc0`/`0xa0` (`0x8c106640/41`).
The game keeps one block per player, `0x224` bytes apart, at `0x8cd85150`
(found by RAM diff, fork `FLYCAST_RAMDUMP`): pd port at +0, a 32-byte action-slot
table at +4 (slot k → pd bit; filled by `0x8c0ad7c8`/`0x8c0ad6a8`, slot 1 B, 2 A,
3 Start, 4–7 D-pad, 9 Y, 10 X, 16 R, 17 L, others 0), and per-bit held/off/press/release
frame counters at +0x24/+0xa4/+0x124/+0x1a4 (`0x8c0ad6e0`).

**The HOLD check.** An interpreter run with the fork's read watch on player 1's
slot table (`FLYCAST_RDWATCH=0cd85154,0cd85174`) logged slot 16 read at
`0x8c0d3892` and slot 9 at `0x8c0d38d2`, both called from `0x8c0d15c6` and `0x8c0d1a74`.
That function (`0x8c0d385c`) tests the **press** counter of slot 16, then of slot 9.
Either one nonzero jumps to HOLD at `0x8c0d38e8`. The slot numbers are 1-byte
immediates (`add #16,r0` / `add #9,r0`). There are only two checks, so a data
patch can only move HOLD from R or Y to C, not add C.

**Patch (`build_gdi.py`, source `tools/hold_c.s`).** Alias C to Y inside the pd
library, in its per-port loop at `0x8c01341e`, right after the decoder fills `on`:
`on |= (on & 1) << 9`, then off/press/release are derived from that, as before.
- **Why Y, not R:** a capability mask applied after decoding keeps only the
  device's `support` bits. That's why the stick's `0xFF` filler never registered as
  R (§Stuck-input legs). The stick's `support` is `0x7ff` (it has Y, not R);
  the pad's is `0xf06fe`.
- Only the positive-logic path is aliased. That's the game's mode: the flag
  `0x8c10663c` comes from the library init and is 0 in RAM. The negative-logic
  path still branches to `0x8c013458` unchanged.
- The original block is unoptimized (it reloads `@r15` for every access). The
  rewrite is the same 58 bytes: 26 instructions plus 3 `nop`s, register use kept to
  r0–r4 (scratch in the SH ABI; the loop reloads them).
- Nothing branches into the block, and no literal points into it (disassembly
  grep). track04 differs from 0.6.0 in `0x3420`–`0x3455` only. New sha1
  `46041d6cd9dddfed491f274510bd9bf05b9165cc`; track01–03 and `.gdi` unchanged.

**Checks (Flycast fork, real BIOS, frame-locked legs as above):**

| leg | compared with | result |
|---|---|---|
| stick, C at 5400/6300 | stick, Y at 5400/6300 (patched) | identical 30/30: C does what Y does |
| CDI, stick, C | CDI, stick, Y | identical 30/30 (HOLD box gets the piece) |
| pad, no press | pad, no press (0.6.0) | identical 32/32 |
| pad, R at 5400/6300 | the same, 0.6.0 | identical 30/30 |
| stick, A at 5400/6300 | stick, no press (patched) | same until the press, then rotates |
| stick, no press | stick, no press (0.6.0) | differs from frame 4800 (the match's first pieces) |
| stick, no press, rewrite with the alias `or` made a `nop` | stick, no press (patched) | identical 33/33 |

The last two rows are the one side effect: on the stick, the new block alone
(without the alias) changes the piece queue the match starts with. The stick's
pd `on`/`press` words were logged every frame (`FLYCAST_PEEK`) and are identical
with and without the patch, so the game gets the same input. The likely cause is
CPU timing feeding the piece randomizer. The seed wasn't traced.

**Also true since the patch:** C does whatever Y does anywhere. Slot 9 is also read
at `0x8c085e1c` (the coin-manager code; Y inserted a coin before free play). Under
free play that has no visible effect (not checked in a leg).

**Not checked:** C in menus; any real arcade stick on hardware.

**Hardware (2026-10-11):** GDEMU with standard DC controllers, "no regression
found" (user report). Real arcade stick: not yet, owed to the user's testers.
Release 0.7.0.

## Soft reset (2026-10-15..22)

**Ask:** A+B+X+Y+Start returns to the Dreamcast BIOS menu.

**What the game has.** No soft reset. Nothing in `1ST_READ.BIN` tests the
five-button mask (`0x60e`), and on 0.7.0 the combo held in a 1P match changes
nothing. The game does carry an exit routine at `0x8c01c454`, library code next to
its BIOS syscall wrappers (`0x8c01c428`–`0x8c01c450`). Unless the IP.BIN byte at
`0x8c0080fc` is 1 (then `0x8c0080fe` = 1 jumps to the bootstrap at `0x8c008300`, and
anything else calls misc r4 = 3), it calls the misc syscall vector `0x8c0000e0` with
r4 = 1, "Exit to BIOS menu" (Flycast `core/reios/reios.cpp:360`). On this disc that
byte is `0x20`, a space in the title field, so it's r4 = 1. Two callers, both in what
looks like debug-window code: `0x8c0676c2`, and `0x8c072a06` (message 17, which first
raises IMASK to 15).

**Patch (`build_gdi.py`, source `tools/pd_update.s`, renamed from `hold_c.s`).** The
same pd per-port block as §HOLD on C, now 102 bytes (`0x8c01341e`–`0x8c013483`, up
to the loop's join at `0x8c013484`). After the positive-logic flag check, the raw `on`
word (before the C alias, so C doesn't stand in for Y) is tested for B, A, Start
(`tst #0x0e` on `~on`), then Y, X (`shlr8`, `tst #0x06`). With all five held:
IMASK = 15 (as the game's own call at `0x8c0729fc`), `MMUCR = 4` (TI: TLB
invalidated; AT = 0: MMU off), then a jump to `0x8c01c454`.
- Room: the negative-logic path (never taken here, §HOLD on C) is rewritten to the
  same press/release in 8 instructions, and the stack scratch word `@(12,r15)` is
  no longer written. Only this block ever touched it (function `0x8c013388`–`0x8c0134bc`).
- Only the block's own two branches target `0x8c013458`–`0x8c013483`, and no word
  in the file points into it.
- Why the MMU goes off: DreamShell, below.
- track04 `f0898932…`, which differs from 0.7.0 in `0x342c`–`0x3482` only. track01–03
  and `.gdi` are unchanged.

**Under DreamShell's ISO Loader.** isoldr redirects the misc syscall vector
(`firmware/isoldr/loader/menu_syscall.s`: `0xac0000e0` → `menu_redir`). r4 = 1 goes
to `menu_exit()` (`syscalls.c:1511`), which reloads DreamShell from `/DS/DS_CORE.BIN`
on the loader's device, the SD here (`utils.c:257`), or starts the BIOS ROM if that
file is missing. isoldr clears bit `0x20` of IP.BIN `0xfc` on start (`main.c:182`), so
the game's exit still takes r4 = 1. It never turns the MMU off on that path
(`loader/mmu.c` `mmu_disable()` has no caller). This game turns it on (`MMUCR =
0x40005` at `0x8c015830`). The game's own library shutdown would turn it off
(`0x8c016e24` → `0x8c015912`, `MMUCR = 0`), but nothing references its wrapper
`0x8c016f70`.

Emulator legs (fork + SD model, §DreamShell tooling; combo at frame 6000, in a match):

| leg | after the combo |
|---|---|
| first build, no MMU off | DreamShell's KOS banner, then `Enabling on-demand Full MMU support`, and Flycast stops: `Fatal: SH4 exception when blocked` |
| shipped build (MMU off) | DreamShell's KOS banner, video set up, no fatal. Then black and no more SD commands: its autostart doesn't relaunch the game |
| control: a 10-instruction program that waits ~3 s and calls misc r4 = 1, MMU never touched | the same writes as the shipped build, then black, no relaunch |
| the same control program, real BIOS, no DreamShell | BIOS menu |
| the game with its `MMUCR = 0x40005` store a `nop` | not usable: the game never starts under isoldr ("Executing…") |

With the MMU off, the game leaves isoldr's exit in the same state as a program that
never touched the MMU. Without it, DreamShell's restart takes an exception while
`SR.BL` = 1 (isoldr's `menu_reboot` loads SR `0x700000f0`), which Flycast treats as
fatal (`core/hw/sh4/sh4_interrupts.cpp:204`). That's right after a TLB entry is
loaded with `MMUCR.AT` still 1 (`core/hw/sh4/modules/fastmmu.cpp:200`). What happens
after DreamShell restarts can't be judged in this rig, since even the clean control
goes black. Real hardware decides.

**Checks (Flycast fork, real BIOS, frame-locked legs, threaded rendering off; shipped
build unless noted):**

| leg | compared with | result |
|---|---|---|
| 0.7.0, pad, combo at 5400 | — | the match goes on (the failing test) |
| pad, combo at 5400 | pad, no press | identical up to the combo, then the BIOS menu |
| stick, combo at 5400 | — | BIOS menu |
| pad, A+B+X+Y at 5400, A+B+X+Start at 6300 | pad, no press | the match goes on; differs from 5520 (Y is HOLD) |
| pad, combo on the title (1950), Start at 2100 | — | exit, then the Start boots the disc again (bootstrap `ac008300`), back to a match |
| CDI, pad, combo at 5400 | — | BIOS menu |
| strict (cache/MMU) build, combo on the title, no later presses | — | BIOS menu, still animating at frame 5280; no exceptions |
| pad, no press | 0.7.0, pad, no press | identical 36/36 |
| stick, no press | 0.7.0, stick, no press | identical 36/36 |
| stick, C at 5400/6300 | stick, Y at 5400/6300 | identical 36/36 |

**Not checked:** ports B–D (the fork drives controller 1 only; the patch runs the same
code for every port record); menus other than the title; any real hardware (GDEMU,
DreamShell).

Release 0.8.0 (emulator-verified; GDEMU and DreamShell owed).
