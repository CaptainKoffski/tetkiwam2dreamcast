#!/usr/bin/env python3
"""mkdiag.py -- serial GD-syscall tracer builds (diagnostic only, never shipped).

  A: build/diag-r4/A-gdi-trace/   the release GDI + tracer (control)
  B: (round 4) make_cdi.py's CDI + tracer, before the G1 unlock; retired
  F: build/diag-r5/F-cdi-unlock-trace/  make_cdi.py's CDI (with the G1 unlock) + tracer v2
     (the tracer runs first, then the unlock stub, then crt0)

Needs `make gdi` done and the sh-elf toolchain at /opt/toolchains/dc. The game's
entry (6 nops at 0x8c010000) jumps to a 64-byte loader appended past the end of
1ST_READ.BIN (crt0's BSS clear wipes it later, after it has run). The loader copies
gdtrace.bin to 0xac004000 (uncached, so instruction fetch sees it), calls
gdtrace_init, then enters crt0 at 0x8c01000c. The 11 GD syscall stubs
(0x8c01c314 + 0x14*func, func 0..10) load the BIOS vector from a literal at stub+0x10
(0x8c0000bc). It now points at hook_vec. docs/kb/cdi.md §round 4.
"""
import os, shutil, struct, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOP = os.path.dirname(os.path.dirname(HERE))
TC = "/opt/toolchains/dc/sh-elf/bin/sh-elf-"
OUT = os.path.join(TOP, "build/diag-r4")
work = os.path.join(TOP, "build/diag-r4/obj")
os.makedirs(work, exist_ok=True)

def run(*a): subprocess.run(a, check=True)
run(TC + "gcc", "-m4-single-only", "-ml", "-Os", "-ffreestanding", "-nostdlib", "-fno-builtin",
    "-ffunction-sections", "-fno-zero-initialized-in-bss", "-Wall", "-c", os.path.join(HERE, "gdtrace.c"),
    "-o", os.path.join(work, "gdtrace.o"))
run(TC + "gcc", "-m4-single-only", "-ml", "-nostdlib", "-Wl,--no-warn-rwx-segments", "-Wl,-e,_gdtrace_init",
    "-T", os.path.join(HERE, "gdtrace.ld"), os.path.join(work, "gdtrace.o"), "-o", os.path.join(work, "gdtrace.elf"))
run(TC + "objcopy", "-O", "binary", os.path.join(work, "gdtrace.elf"), os.path.join(work, "gdtrace.bin"))
syms = {l.split()[2]: int(l.split()[0], 16) for l in
        subprocess.run([TC + "nm", os.path.join(work, "gdtrace.elf")], capture_output=True, text=True, check=True).stdout.splitlines()
        if len(l.split()) == 3}
BLOB = open(os.path.join(work, "gdtrace.bin"), "rb").read()
BLOB += b"\0" * (-len(BLOB) % 4)
assert syms["_gdtrace_init"] == 0x8c004000 and len(BLOB) < 0x4000, "tracer must start at 0x8c004000 and fit 16 KB"
HOOK_VEC = syms["_hook_vec"]

def add_tracer(boot):
    boot = bytearray(boot)
    cont = 0x8c01000c                                    # crt0, past the 6 entry nops
    if boot[:8] == struct.pack("<4H", 0xd001, 0x402b, 9, 9):
        cont = struct.unpack_from("<I", boot, 8)[0]       # make_cdi.py's unlock hook: chain to it
    else:
        assert boot[:12] == bytes.fromhex("0900") * 6, "entry is not 6 nops"
    for f in range(11):                                  # GD syscall stubs, func 0..10
        s = 0xc314 + 0x14 * f
        assert boot[s:s + 2] == b"\x00\xe6" and struct.unpack_from("<I", boot, s + 0xc)[0] == f, f"stub {f} moved"
        assert struct.unpack_from("<I", boot, s + 0x10)[0] == 0x8c0000bc, f"stub {f} vector literal"
        struct.pack_into("<I", boot, s + 0x10, HOOK_VEC)
    boot += b"\0" * (-len(boot) % 4)
    H = 0x8c010000 + len(boot)
    boot[0:12] = struct.pack("<4HI", 0xd001, 0x402b, 9, 9, H)          # mov.l @(8),r0; jmp @r0; nop; nop; .long H
    loader = struct.pack("<14H5I",
        0xd106, 0xd207, 0xd307,          # r1 = src, r2 = 0xac004000, r3 = words
        0x6016, 0x2202, 0x4310, 0x8ffb, 0x7204,  # A: r0=*r1++; *r2=r0; dt r3; bf.s A; r2+=4
        0xd005, 0x400b, 9,               # r0 = gdtrace_init; jsr @r0; nop
        0xd005, 0x402b, 9,               # r0 = cont; jmp @r0; nop
        H + 0x40, 0xac004000, len(BLOB) // 4, 0x8c004000, cont)
    boot += loader.ljust(0x40, b"\0") + BLOB
    return boot

if __name__ == "__main__":
    gdi = os.path.join(TOP, "build/gdi")
    # A: GDI + tracer (1ST_READ lives in track04; fix its root-dir size in track03)
    a = os.path.join(OUT, "A-gdi-trace"); shutil.rmtree(a, ignore_errors=True); shutil.copytree(gdi, a)
    t3 = bytearray(open(os.path.join(a, "track03.iso"), "rb").read())
    p = t3.find(b"1ST_READ.BIN;1", 20 * 2048, 21 * 2048) - 33
    size = struct.unpack_from("<I", t3, p + 10)[0]
    nb = add_tracer(open(os.path.join(a, "track04.iso"), "rb").read()[:size])
    open(os.path.join(a, "track04.iso"), "wb").write(nb.ljust(max(300 * 2048, -(-len(nb) // 2048) * 2048), b"\0"))
    struct.pack_into("<I", t3, p + 10, len(nb)); struct.pack_into(">I", t3, p + 14, len(nb))
    open(os.path.join(a, "track03.iso"), "wb").write(t3)
    print(f"A: GDI 1ST_READ {size} -> {len(nb)} B, hook_vec {HOOK_VEC:#x}, tracer {len(BLOB)} B")
    # F: make_cdi.py, with add_tracer applied after all of its patches
    s = open(os.path.join(TOP, "make_cdi.py")).read().replace(
        'HERE = os.path.dirname(os.path.abspath(__file__))', f'HERE = "{TOP}"')
    anchor = 'open(os.path.join(work, "1ST_READ.BIN"), "wb").write(boot)'   # after all of make_cdi's patches
    assert s.count(anchor) == 1
    s = s.replace(anchor, f'import sys; sys.path.insert(0, "{HERE}"); from mkdiag import add_tracer; boot = add_tracer(boot)\n' + anchor)
    open(os.path.join(work, "make_cdi_trace.py"), "w").write(s)
    run(sys.executable, os.path.join(work, "make_cdi_trace.py"), gdi, os.path.join(TOP, "build/diag-r5/F-cdi-unlock-trace"))
