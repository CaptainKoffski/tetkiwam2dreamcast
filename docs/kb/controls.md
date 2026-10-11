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
