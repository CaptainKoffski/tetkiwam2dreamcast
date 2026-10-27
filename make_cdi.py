#!/usr/bin/env python3
"""make_cdi.py [gdidir] [outdir] -- burnable audio/data MIL-CD CDI from the built GDI.

Reads build_gdi.py's output, so the cover art, title and free-play byte carry
over: track03's ISO9660 tree is unpacked file by file, 1ST_READ.BIN comes from
track04, and mkdcdisc masters a fresh CD with its own CD-native IP.BIN (branded
from the GD IP's fields + iplogo.mr). senkosp2dreamcast tooling.md §CDI mastering
proved it on GDEMU: a retail GD IP.BIN dies on a real CD boot, mkdcdisc's boots.
1ST_READ.BIN goes on the disc unscrambled, as in a scene binhack CDI, so
DreamShell's ISO Loader can run it from an SD card. That IP.BIN's bootstrap is
hooked to scramble it back in RAM after a CD boot has unscrambled it
(tools/ip_rescramble.s).

Three code changes on top of the GDI, all because Katana assumes a GD-ROM boot:
the selfboot "LBA hack" (LBA_SITES), the GDFS disc-type check (CHECK, which
becomes the CD read-mode setup) and the G1 bus unlock at entry. docs/kb/cdi.md. Output: <outdir>/tetris.cdi + README.txt (burn notes).
"""
import os, struct, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
GDI = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "build/gdi")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "build/cdi")
# mkdcdisc v0.0.4 (gitlab.com/simulant/mkdcdisc 2b98b0d), built in the sibling; tooling.md §CDI
MKDCDISC = os.environ.get("MKDCDISC", os.path.join(HERE, "../senkosp2dreamcast/tools/mkdcdisc/build/mkdcdisc"))

# file offset in 1ST_READ.BIN (loads at 0x8c010000) -> GD FAD it holds. Literal-
# pool words of the Katana GDFS: gdFsInit's TOC check (0x8c010b52: HD track 3 must
# start at FAD 45150, else it returns -51 but mounts anyway), the fad < 45150 -> -32 guards of the
# two read paths (0x8c01129c, 0x8c0115ec), and the PVD FAD gdFsInit reads
# (0x8c010b62 -> word 0x8c0d5b10 = 45150 + 16). On CD the data track starts at
# MSINFO, so every one shifts by the same delta. No other 45150/45166 word in the
# file; __GAME__/__TEST__.BIN hold some too but are Naomi leftovers 1ST_READ never
# names (strings), so they ship untouched.
LBA_SITES = {0xc34: 45150, 0x12e8: 45150, 0x16b4: 45150, 0xc5b10: 45166}

assert os.access(MKDCDISC, os.X_OK), f"mkdcdisc missing at {MKDCDISC} (MKDCDISC= to override): docs/kb/tooling.md §CDI"

def unscramble(data):
    """What a CD boot does to the boot file as it loads it: Marcus Comstedt's scramble.c
    (public domain), mkdcdisc src/third_party/scramble unscramble(). 32-byte slices are
    shuffled within power-of-two chunks from 2 MB down; a tail under 32 bytes stays."""
    out, seed, pos, left, chunk = bytearray(data), len(data) & 0xffff, 0, len(data), 0x200000
    while chunk >= 32:
        while left >= chunk:
            n = chunk // 32
            idx = list(range(n))
            for k, i in enumerate(range(n - 1, -1, -1)):
                seed = (seed * 2109 + 9273) & 0x7fff
                x = (((seed + 0xc000) & 0xffff) * i) >> 16
                idx[i], idx[x] = idx[x], idx[i]
                out[pos + 32 * idx[i]:pos + 32 * idx[i] + 32] = data[pos + 32 * k:pos + 32 * k + 32]
            pos, left = pos + chunk, left - chunk
        chunk >>= 1
    return bytes(out)

# tools/ip_rescramble.s, assembled (the recipe is in its header). It sits at IP.BIN 0x6200
# (0x8c00e200): size word, the plain first 16 bytes, then the code at +0x20.
IP_HOOK, IP_HOOK_AT, IP_GAME_PTR = bytes.fromhex(
    "00000000000000000000000000000000000000000000000000000000000000002a0831d431d0436104e20663"
    "16653035038b1042f98b46a009002dd002655d662cd772353b8b73690949094901492adb00eab36da12d017a"
    "923afb8f027d27dc936aff7a4c9007061a064a900c364990092648906c300d6da70d1a0d294ddc3dbc3da361"
    "1c31bc31d1621163312d21212d620842084200424c3208e32660022c1043fb8f047ca82adb8b14dc73630943"
    "c66002241043fb8f0474c2af7835014720e00237bd892a4800e11362136313651366136713681369136a136b"
    "136c136d136e01d02b4003640000018c04e2008c00e2008c000020000000a08c0000808c3d083924ff7f00c0"), 0x6200, 0x60ac
iso = open(os.path.join(GDI, "track03.iso"), "rb").read()
sec = lambda lba: (lba - 45000) * 2048
work = tempfile.mkdtemp()
boot = None

def walk(lba, size, path):                     # ISO9660 dir records, absolute LBAs from 45000
    global boot
    os.makedirs(path, exist_ok=True)
    p, end = sec(lba), sec(lba) + size
    while p < end:
        if not iso[p]:                          # records never straddle a sector
            p = (p // 2048 + 1) * 2048
            continue
        ext, sz = struct.unpack_from("<I", iso, p + 2)[0], struct.unpack_from("<I", iso, p + 10)[0]
        name = iso[p + 33:p + 33 + iso[p + 32]].decode().split(";")[0]
        if iso[p + 25] & 2:
            if name not in ("\0", "\1"):
                walk(ext, sz, os.path.join(path, name))
        elif name == "1ST_READ.BIN":            # extent points at track04 (LBA 450000)
            boot = bytearray(open(os.path.join(GDI, "track04.iso"), "rb").read()[:sz])
        else:
            open(os.path.join(path, name), "wb").write(iso[sec(ext):sec(ext) + sz])
        p += iso[p]

root = struct.unpack_from("<I", iso, 0x8000 + 158)[0], struct.unpack_from("<I", iso, 0x8000 + 166)[0]
walk(*root, os.path.join(work, "root"))
assert boot, "1ST_READ.BIN not in the GDI filesystem"
boot_size = len(boot)

msinfo = int(subprocess.run([MKDCDISC, "-M", "-o", os.path.join(work, "x.cdi")],
                            check=True, capture_output=True, text=True).stdout.split()[-1])
for v in set(LBA_SITES.values()):
    found = {i for i in range(0, len(boot) - 3, 4) if boot[i:i + 4] == struct.pack("<I", v)}
    assert found == {o for o, w in LBA_SITES.items() if w == v}, f"unexpected FAD {v} words in 1ST_READ.BIN"
for o, v in LBA_SITES.items():
    struct.pack_into("<I", boot, o, v - 45000 + msinfo)
# GD-only mount: gdFsInit compares the drive's disc type with 0x80 (GD-ROM) at
# 0x8c010aac..0x8c010ab9 and bails before the PVD read on anything else (on the CDI
# the next FS read was FAD 0). And the game never calls the GDROM sector-mode syscall
# (func 10, stub 0x8c01c3dc, no caller), so after its drive init the BIOS reads in
# its default Mode 1 (CD_READ expected data type 2, fork GDREAD trace) -- right for
# a GD's HD area, wrong for this CD's Mode 2 Form 1 track (the BIOS boots it with
# type 4). Flycast ignores the field; GDEMU hung on a black screen after the TM logo.
# KOS sets track type 2048 on CD-ROM XA, 1024 otherwise (kernel/arch/dreamcast/
# hardware/cdrom.c cdrom_change_datatype). So the check's 14 bytes become
# "jsr helper", and the helper -- in two syscall stubs nothing references (MISC
# r6=-1 funcs 0/1) -- tail-calls the func-10 stub with KOS's XA params
# {set, data area 0x2000, 2048, 2048}. The check's 0x0080 literal word becomes
# the helper address. Nothing else loads from, or branches into, any of it.
CHECK, LIT, HELPER = 0xaac, 0xad4, 0xc3f0              # file offsets (+0x8c010000)
assert boot[CHECK:CHECK + 14].hex() == "f3521194226340330189f9a00900" and boot[LIT:LIT + 4] == b"\x80\0\0\0", \
    "unexpected 1ST_READ.BIN at the disc-type check"
assert boot[HELPER:HELPER + 40].hex() == "ffe602d702d002602b40090000000000bc00008c" \
                                         "ffe602d702d002602b40090001000000bc00008c", "unexpected MISC syscall stubs"
boot[CHECK:CHECK + 14] = struct.pack("<7H", 0xd109, 0x410b, 9, 9, 9, 9, 9)  # mov.l @(LIT),r1; jsr @r1; nop x5
struct.pack_into("<I", boot, LIT, 0x8c010000 + HELPER)
boot[HELPER:HELPER + 40] = struct.pack("<12H4I", 0xc705, 0xaff3, 0x6403,     # mova params,r0; bra stub10; mov r0,r4
                                        *[9] * 9, 0, 0x2000, 2048, 2048)    # nop pad; params at HELPER+0x18
assert len(boot) == boot_size, "a patch changed 1ST_READ.BIN's length"   # bytearray slices resize silently
# G1 bus unlock. Holly gates the GD-ROM's ATA bus until it has watched the whole
# BIOS cross it: write the size to 0xa05f74e4, then read every word. The boot ROM
# does it at reset (0xa000034a) and has a routine that writes 0x42fe there with no
# read (0xa0004ae8). KOS redoes it in cdrom_init (kernel/arch/dreamcast/hardware/
# cdrom.c:781-797) and binhack's IP.HAK bootstrap does too (0x8c00e1a4), so a
# homebrew or scene CDI never sees a locked bus; Katana doesn't, and on GDEMU the
# game's first GD command sat in its data phase forever (round 4). Flycast ignores
# the register (core/hw/holly/sb.cpp:204), so only hardware shows it. The entry's 6
# nops jump to this stub past the end of the file (crt0 clears it as BSS afterwards).
# ponytail: no 0xe6ff custom-BIOS branch (KOS reads 1 KB there); add it if one hangs.
boot += b"\0" * (-len(boot) % 4)
assert boot[:12] == bytes.fromhex("0900") * 6, "entry is not 6 nops"
boot[:12] = struct.pack("<4HI", 0xd001, 0x402b, 9, 9, 0x8c010000 + len(boot))  # mov.l @(8),r0; jmp @r0
boot += struct.pack("<12H4I", 0xd105, 0xd006, 0x2102,      # *(u32 *)0xa05f74e4 = 0x1fffff
                    0xd006, 0xe208, 0x4228,                  # r0 = BIOS, r2 = 0x80000 words
                    0x4210, 0x8ffd, 0x6106,                  # A: dt r2; bf.s A; r1 = *r0++
                    0xd004, 0x402b, 9,                       # jmp crt0 (past the hook)
                    0xa05f74e4, 0x1fffff, 0xa0000000, 0x8c01000c)
open(os.path.join(work, "1ST_READ.BIN"), "wb").write(boot)
# The hook skips the rescramble when the first 16 bytes are already plain, so a CD boot
# must never leave them plain.
assert unscramble(bytes(boot))[:16] != boot[:16], "a CD boot would leave 1ST_READ.BIN's head plain"

# IP.BIN fields mirrored from the GD IP (makeip src/field.c offsets). Area stays
# mkdcdisc's JUE, as in the sibling. Two passes: the first (-N -I, only to get the data
# track) has mkdcdisc fill in its IP.BIN; that IP.BIN, hooked, masters the disc (-p takes
# it as is). -B: 1ST_READ.BIN goes on the disc unscrambled (module docstring).
f = lambda a, b: iso[a:b].decode().strip()
base = [MKDCDISC, "-q", "--allow-overwrite", "-B", os.path.join(work, "1ST_READ.BIN"),
        "-D", os.path.join(work, "root")]
fields = ["-n", f(0x80, 0x100), "-a", f(0x70, 0x80), "-s", f(0x40, 0x4a),
          "-P", f(0x4a, 0x50), "-r", f(0x50, 0x58), "-H", f(0x38, 0x3f)]
MR = os.path.join(HERE, "iplogo.mr")
fields += ["-i", MR] if os.path.exists(MR) else []
print("iplogo.mr: TM screen logo inserted" if os.path.exists(MR) else "note: no iplogo.mr -> mkdcdisc's stock license screen")
subprocess.run(base + fields + ["-N", "-I", "-o", os.path.join(work, "ip.cdi")], check=True)
ip = bytearray(open(os.path.join(work, "ip.iso"), "rb").read()[:0x8000])
assert ip[:16] == b"SEGA SEGAKATANA " and ip[IP_GAME_PTR:IP_GAME_PTR + 4] == struct.pack("<I", 0x8c010000), \
    "unexpected mkdcdisc bootstrap (game entry pointer)"
assert not any(ip[IP_HOOK_AT:]), "IP.BIN 0x6200.. is not free"
hook = bytearray(IP_HOOK)
struct.pack_into("<I16s", hook, 0, len(boot), bytes(boot[:16]))
ip[IP_HOOK_AT:IP_HOOK_AT + len(hook)] = hook
struct.pack_into("<I", ip, IP_GAME_PTR, 0x8c008000 + IP_HOOK_AT + 0x20)
open(os.path.join(work, "IP.BIN"), "wb").write(ip)
os.makedirs(OUT, exist_ok=True)
subprocess.run(base + ["-p", os.path.join(work, "IP.BIN"), "-o", os.path.join(OUT, "tetris.cdi")], check=True)
open(os.path.join(OUT, "README.txt"), "w").write("""\
TETRIS KIWAMEMICHI -- Dreamcast conversion, CD-R (CDI) build
=============================================================

tetris.cdi is a self-booting audio/data MIL-CD image. Burn it as a DISC
IMAGE with a CDI-aware burner (Padus DiscJuggler, Alcohol 120%, ImgBurn
via a converter); do not extract it or burn its contents as files. Older
Dreamcast lasers like slow burns: 8x or lower on a quality CD-R.

Late-2000+ Dreamcasts that block MIL-CD cannot boot any burned CD -- that
is the console, not the disc. GDEMU/ODE users: use the [GDI] release.
""")
subprocess.run(["rm", "-rf", work])
print(f"OK  {OUT}/tetris.cdi  (data track at LBA {msinfo}, GDFS FADs {sorted(set(LBA_SITES.values()))} -> {msinfo - 45000:+d})")
