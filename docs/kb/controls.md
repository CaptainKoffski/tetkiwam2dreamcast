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
| X, L trigger, C, Z | nothing: identical to the no-press leg | — |
| Start | title and menus (every leg reached the match on Start alone) | ✅ |

So on the stick: rotate with A and B (bottom row), hold with Y (top row),
move and drop with the lever. X, C and Z do nothing.

**Not checked:** lever down and right (they're the same D-pad bits as the pad's,
so presumably soft drop and move right); which way A and B turn; menu buttons
other than Start; the Naomi original's button layout; and any real arcade stick
on hardware. The remaining hardware question is whether a real HKT-7300 declares
no analog axes the way Flycast's model does.
