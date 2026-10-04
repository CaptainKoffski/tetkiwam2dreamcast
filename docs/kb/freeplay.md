# Free play (2026-10-04)

**Ask:** players shouldn't have to insert a coin (Y) before every game.

**Finding:** the DC build already contains free play. `1ST_READ.BIN` (loads at
0x8c010000) has a coin-manager object with a live block at `+0x940`, which is
memcpy'd (108 B) every frame to a snapshot at `+0x8c4` (`0x8c087938`):

| live | snapshot | meaning (from the code that uses it) |
|---|---|---|
| +0x940 / +0x950 | +0x8c4 / +0x8d4 | slot 1 / slot 2 credits (capped at 9, `0x8c085e50`) |
| +0x944 / +0x954 | +0x8c8 / +0x8d8 | coins toward the next credit |
| +0x948 / +0x958 | +0x8cc / +0x8dc | coins per credit (init 2) |
| +0x980 | +0x904 | **free play** (init 0) |
| +0x984 | +0x908 | chute type (1 = "INDEVIDUAL", else "COMMON", debug print `0x8c085cde`) |
| +0x98c.. | | credits per start, per sequence (init 1) |

`0x8c087818` (has credit) and `0x8c0877a0` (spend credit) both start with
`if (this[0x904]) return 1;`. The attract/credit overlay (`0x8c0860d6` and about
17 other readers) takes the "can start" branch on the same word. Only the init
(`0x8c0845e2`) writes `+0x980`. The Naomi build would fill it from coin
setting #27 (Flycast `core/hw/naomi/naomi_flashrom.cpp`: `ForceFreePlay` →
EEPROM byte 9 = 26). The DC build has no EEPROM and leaves it 0.

**Patch (`build_gdi.py`, always on):** at `0x8c0845e2`, `mov.l r3,@(r0,r12)`
(0x0c36, r3 = 0) → `mov.l r1,@(r0,r12)` (0x0c16). r1 is 1 from `mov #1,r1` at
`0x8c0845be` and is unchanged through the store. File offset 0x745e2,
`0x36` → `0x16`, original byte asserted. Tooling: `sh-elf-objdump -D -b binary
-m sh4 -EL --adjust-vma=0x8c010000 1st_read.bin`.

**Checks (2026-10-04):**
- Byte diff: track04 differs from 0.3.0 at 0x745e2 only. tetris.gdi and
  track01/02/03 are unchanged (track03 `05ab2d08…`). New track04 sha1
  `2718605b6947bad281ea81283212cccb1f29d534`.
- Flycast fork + real BIOS, stock build run side by side as the control:
  - attract overlay: stock shows INSERT COIN(S) / CREDIT(S) 0, patched shows
    PRESS START BUTTON / FREE PLAY (the game's own art).
  - scripted Start (`FLYCAST_START_AT=1800,2040,2280,2520`, see `tooling.md`):
    patched goes intro → title → play-style select ("プレイスタイル選択!",
    FREE PLAY in the corner) with 0 credits. Stock stays in attract.
- Not checked: a full game played to game over / continue in the emulator.
  The continue path uses the same two functions.

**Hardware verdict (2026-10-04):** "works on GDEMU" (user report), one-round
close. Release 0.4.0: track04 `2718605b…`, everything else as 0.3.0.
