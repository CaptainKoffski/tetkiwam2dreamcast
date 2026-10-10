#!/usr/bin/env python3
"""build_gdi.py [outdir] -- build a Dreamcast GDI from the Tetris Kiwamemichi GD-ROM.

The arcade disc's TETRIS.BIN (DES key from the game's PIC, 317-5093-jpn) decrypts
to a 0x500-byte Naomi header followed by a complete DC GD track-3 ISO (IP.BIN +
filesystem, absolute LBAs from 45000) -- TCRF, Notes:Tetris_Kiwamemichi_(Arcade).

Trimming alone does NOT boot on the real DC BIOS (Flycast + dc_boot.bin falls to
the BIOS menu; reios boots it). Moving 1ST_READ.BIN to the first sector of a last
data track at LBA 450000 does -- same finding as cleopatra phase4-conversion B4.
Tracks 1/2 are the arcade disc's own. Output: <outdir>/tetris.gdi + 4 tracks.
"""
import os, struct, subprocess, sys, tempfile, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
# romset dir holding tetkiwam.zip + tetkiwam/gdl-0020.chd (never copied into this repo)
ROMS = os.environ.get("NAOMI_DIR", os.path.join(HERE, "../naomi2dreamcast/naomi"))
SET = os.path.join(ROMS, "tetkiwam")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "build/gdi")
TRACK4_LBA = 450000

os.makedirs(OUT, exist_ok=True)
work = tempfile.mkdtemp()
subprocess.run(["chdman", "extractcd", "-f", "-i", os.path.join(SET, "gdl-0020.chd"),
                "-o", os.path.join(work, "disc.gdi")], check=True, capture_output=True)
pic = os.path.join(work, "317-5093-jpn.pic")
with zipfile.ZipFile(os.path.join(ROMS, "tetkiwam.zip")) as z, open(pic, "wb") as f:
    f.write(z.read("317-5093-jpn.pic"))
exe = os.path.join(HERE, "build/extract_dat")
subprocess.run(["clang++", "-O2", "-std=c++17", "-w", os.path.join(HERE, "tools/extract_dat.cpp"), "-o", exe], check=True)
dec = os.path.join(work, "TETRIS.dec")
subprocess.run([exe, pic, os.path.join(work, "disc03.bin"), dec, "2352"], check=True,
               env={**os.environ, "EXTRACT_NAME": "TETRIS.BIN"})

with open(dec, "rb") as f:
    f.seek(0x500)
    iso = bytearray(f.read())
assert iso[:16] == b"SEGA SEGAKATANA ", "no DC IP.BIN after the Naomi header"
blocks = struct.unpack_from("<I", iso, 0x8000 + 80)[0]       # PVD volume space size
iso = iso[:blocks * 2048]

sec = lambda lba: (lba - 45000) * 2048
root = struct.unpack_from("<I", iso, 0x8000 + 158)[0]
p = sec(root)
while iso[p]:
    if iso[p + 33:p + 33 + iso[p + 32]] == b"1ST_READ.BIN;1":
        ext, size = struct.unpack_from("<I", iso, p + 2)[0], struct.unpack_from("<I", iso, p + 10)[0]
        boot = bytes(iso[sec(ext):sec(ext) + size])
        struct.pack_into("<I", iso, p + 2, TRACK4_LBA)
        struct.pack_into(">I", iso, p + 6, TRACK4_LBA)
        break
    p += iso[p]
else:
    sys.exit("1ST_READ.BIN not in root directory")

# Free play: the coin object's init (0x8c0845e2) stores 0 to its free-play word
# (+0x980, copied every frame to +0x904). The credit check (0x8c087818) and credit
# spend (0x8c0877a0) test that word first and succeed when it is set, and the
# attract/credit display takes its "can start" branch. The Naomi build would fill it
# from coin setting #27 (Flycast core/hw/naomi/naomi_flashrom.cpp ForceFreePlay);
# this DC build never does. Store r1 (=1 there) instead of r3 (=0):
# mov.l r3,@(r0,r12) 0x0c36 -> mov.l r1,@(r0,r12) 0x0c16. 1ST_READ loads at 0x8c010000.
FREEPLAY = 0x8c0845e2 - 0x8c010000
assert boot[FREEPLAY:FREEPLAY + 2] == b"\x36\x0c", "unexpected 1ST_READ.BIN at the free-play site"
boot = boot[:FREEPLAY] + b"\x16" + boot[FREEPLAY + 1:]

# DMA reads with a P1 buffer address, for DreamShell's ISO Loader from SD. The game
# turns the SH4 MMU on (MMUCR = 0x40005 at 0x8c015830; it maps the store queues
# through the TLB). Its Katana gdc read request (0x8c01032a) hands the GD syscall
# DMA buffers as physical addresses (buf & 0x1fffffff -> 0x0c...), which is a
# translated U0 address once the MMU is on. Real GD DMA never goes through the MMU,
# but isoldr's SD firmware has no DMA: it copies the sectors to that address with
# the CPU and takes a TLB miss into the game's crash handler (black, no sound).
# Widen the mask literal to 0xffffffff so DMA reads pass the caller's P1 address
# (PIO reads still OR in 0xa0000000). Holly keeps only bits 28:5 of SB_GDSTAR
# (Flycast core/hw/holly/sb.cpp:385), so real DMA lands at the same RAM.
DMAMASK = 0x8c010508 - 0x8c010000
assert boot[DMAMASK:DMAMASK + 4] == b"\xff\xff\xff\x1f", "unexpected 1ST_READ.BIN at the gdc DMA mask"
boot = boot[:DMAMASK + 3] + b"\xff" + boot[DMAMASK + 4:]

# Disc art: the DC BIOS disc menu and GDEMU's menu draw the root-dir 0GDTEX.PVR
# (shipped here as Sega's leftover "Pokekano" CD picture: GBIX+PVRT header,
# ARGB1555 square-twiddled 256x256). Optional 0GDTEX.PVR at repo root -- bare
# PVRT, RGB565 rectangle (raw scanlines) 256x256 -- is Morton-twiddled over the
# donor's pixels in place, same twiddle + in-place overwrite as senkosp2dreamcast
# make_gdi.py patch_gdtex (hardware-verified there); only the header's pixel-
# format byte changes to RGB565. Gitignored (cover art); absent -> donor art.
ART = os.path.join(HERE, "0GDTEX.PVR")
if os.path.exists(ART):
    pvr = open(ART, "rb").read()
    assert pvr[:4] == b"PVRT" and pvr[8:16] == b"\x01\x09\x00\x00\x00\x01\x00\x01" and len(pvr) == 16 + 131072, \
        "bad 0GDTEX.PVR: need bare PVRT, RGB565 rectangle, 256x256"
    p = iso.find(b"0GDTEX.PVR;1", sec(root), sec(root) + 2048) - 33
    assert p > sec(root), "0GDTEX.PVR not in root directory"
    o = sec(struct.unpack_from("<I", iso, p + 2)[0])
    assert struct.unpack_from("<I", iso, p + 10)[0] == 32 + 131072 and iso[o:o + 4] == b"GBIX" and \
        iso[o + 16:o + 20] == b"PVRT" and iso[o + 25:o + 32] == b"\x01\x00\x00\x00\x01\x00\x01", \
        "donor 0GDTEX.PVR not GBIX+PVRT square-twiddled 256x256"
    # twiddle = Morton order, y bits even, x bits odd (Flycast core/rend/texconv.cpp twiddle_slow)
    sp = [sum(((v >> b) & 1) << (2 * b) for b in range(8)) for v in range(256)]
    for y in range(256):
        for x in range(256):
            d, s = o + 32 + (sp[y] | sp[x] << 1) * 2, 16 + (y * 256 + x) * 2
            iso[d:d + 2] = pvr[s:s + 2]
    iso[o + 24] = 1                               # PVRT pixel format: RGB565
print("0GDTEX.PVR: disc art replaced" if os.path.exists(ART) else "note: no 0GDTEX.PVR -> donor disc art")

# Game title: IP.BIN 0x80, 128 B space-padded (Flycast core/reios/reios.h ip_meta_t
# software_name; makeip src/field.c "Game Title"). Shipped as Sega's "THIS IS A SAMPLE
# DISK FOR USE IN THE OFFICE ONLY ..."; GDEMU menus and Flycast show this field. The
# header CRC at 0x20 covers only 0x40-0x4F (makeip src/crc.c update_crc), so no fixup.
iso[0x80:0x100] = b"TETRIS KIWAMEMICHI".ljust(128)

# SEGA TM screen logo: IP.BIN's MR-image slot at 0x3820 (makeip src/mr.c MR_OFFSET;
# mc.pp.se/dc/ip.bin.html: 0x3800-0x5FFF is modifiable bootstrap). The shipped
# IP.BIN leaves the 8 KB slot zeroed and its license code holds the slot pointer
# 0x8c00b820 at 0x083c, so a logo dropped in is drawn as-is. Optional, gitignored
# (Sega trademark art); absent -> blank slot, build identical to before.
MR = os.path.join(HERE, "iplogo.mr")
if os.path.exists(MR):
    mr = open(MR, "rb").read()
    assert mr[:2] == b"MR" and struct.unpack_from("<I", mr, 2)[0] == len(mr) and len(mr) <= 8192, "bad iplogo.mr"
    assert iso[0x3820:0x5820] == bytes(8192), "IP.BIN logo slot not empty"
    iso[0x3820:0x3820 + len(mr)] = mr
print("iplogo.mr: TM screen logo inserted" if os.path.exists(MR) else "note: no iplogo.mr -> blank TM screen")

open(os.path.join(OUT, "track03.iso"), "wb").write(iso)
open(os.path.join(OUT, "track04.iso"), "wb").write(boot.ljust(max(300, -(-size // 2048)) * 2048, b"\0"))
os.replace(os.path.join(work, "disc01.bin"), os.path.join(OUT, "track01.bin"))
os.replace(os.path.join(work, "disc02.raw"), os.path.join(OUT, "track02.raw"))
gdi = open(os.path.join(work, "disc.gdi")).read().split("\n")
lba2 = gdi[2].split()[1]                                       # keep the arcade disc's track-2 LBA
open(os.path.join(OUT, "tetris.gdi"), "w").write(
    f"4\n1 0 4 2352 track01.bin 0\n2 {lba2} 0 2352 track02.raw 0\n"
    f"3 45000 4 2048 track03.iso 0\n4 {TRACK4_LBA} 4 2048 track04.iso 0\n")
subprocess.run(["rm", "-rf", work])
print(f"OK  {OUT}/tetris.gdi  (1ST_READ {size} B -> LBA {TRACK4_LBA})")
