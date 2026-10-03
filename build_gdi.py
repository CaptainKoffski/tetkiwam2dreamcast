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
