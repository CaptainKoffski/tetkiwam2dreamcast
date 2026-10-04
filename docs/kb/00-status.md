# Project status

**Updated:** 2026-10-04 — **Release 0.1.0 (tag, on `main`): the shipped
Dreamcast build of Tetris Kiwamemichi boots on real hardware (GDEMU) with
the NAOMI GD-ROM SYSTEM logo on the SEGA TM screen.** Scope is a
conversion, not a port (README): the arcade GD-ROM carries a finished DC
build; we decrypt it, relocate `1ST_READ.BIN` to a last data track, and
(0.1.0) fill IP.BIN's empty logo slot. Honest limit: single-rig evidence —
one console, one GDEMU, one user report per round.

Layout mirrors senkosp2dreamcast: this file is the narrative index,
`tooling.md` holds recipes/citations/checksums, one file per step holds
the full record (`iplogo.md`).

**IPLOGO CLOSED (2026-10-04, operator hardware verdict): "works on
GDEMU" — the NAOMI logo on the SEGA TM screen holds on real silicon,
one-round close.** **Release 0.1.0 PROMOTED:** track03 sha1 =
`736cbb18b0c39acc395a46b0692d8ae25dfa0e8f` (first track03 change since
the base build), tracks 01/02/04 + gdi unchanged; branch `iplogo`
fast-forwarded into `main`, annotated tag `0.1.0`, both pushed; respin
from defaults byte-identical (needs the gitignored `iplogo.mr` at repo
root). Full record: `iplogo.md`.

**IPLOGO ROUND 1 SHIPPED (2026-10-04, branch `iplogo`): NAOMI logo on
the SEGA TM screen.** Same mechanism as senkosp2dreamcast T12: the
screen's image is IP.BIN's MR-logo slot (track03 offset 0x3820, 8192 B —
makeip `src/mr.c:39` MR_OFFSET), measured as exactly that zero run in the
shipped IP.BIN, with the license code's `0x8c00b820` literal at 0x083c
pointing at it. Fix: `build_gdi.py` writes the gitignored `iplogo.mr`
(same file as the sibling; decoded + viewed = NAOMI™ GD-ROM SYSTEM logo,
320×90/63 colors/6807 B) into the slot before track03 is written. Control
build without the file = the README's prior track03 sha1 exactly; with
it, only 0x3820..0x52b5 differ. **Beyond the sibling's round 1:** the
license screen was actually seen in the emulator — real BIOS in the
instrumented Flycast fork, guest-framebuffer dump extended to 0888 for
the purpose (fork commit `ab2196447`). Hardware round owed: TM screen
shows the logo + boot regression.

**BASE BUILD (2026-10-03): DC-bootable GDI from the arcade GD-ROM; GDEMU
confirmed by user report the same day.** Record is the README ("How it
works") and the git log (`75fc7b6`, `de57383`); no KB existed yet.
