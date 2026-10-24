# Working style

1. **Verify on the real target.** A passing proxy — emulator, mock, staging —
   is not proof it works in production or on real hardware. Drive the real
   thing before claiming it works.
2. **Control-test when stuck on "does it work at all."** Run a known-good
   reference through the same path before theorizing about your own artifact.
   It isolates "my bytes" from "the process" in one step.
3. **Every hardware/behavioral claim carries a citation, and primary sources
   outrank wikis** — emulator/kernel/library source beats a wiki or a forum
   post.
4. **Record every tool install** — version, flags, exact steps — so the
   pipeline stays reproducible by someone (or some session) that wasn't there.
5. **Never commit or upload copyrighted dumps** — ROMs, BIOS images, disc
   images. Keep them gitignored. Ship method, tools, and patches; never the
   copyrighted bytes.

# Flycast fork

Always launch `../flycast4naomi2dreamcast` builds with `FLYCAST_HEADLESS=1`
(hidden window, background app, null audio; `FLYCAST_SHOT` dumps still work).
Never run it with a visible window or sound unless the user asks for one.
