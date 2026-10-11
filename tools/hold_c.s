! HOLD on C: replacement for 1ST_READ.BIN 0x8c01341e..0x8c013457 (58 bytes), Sega pd
! library per-port update. Makes the arcade stick's C (bit 0) a copy of Y (bit 9, HOLD)
! before off/press/release are derived. build_gdi.py carries the bytes; this is their source.
! Rebuild and print them:
!   B=/opt/toolchains/dc/sh-elf/bin
!   $B/sh-elf-as -little tools/hold_c.s -o /tmp/hold_c.o
!   $B/sh-elf-objcopy -O binary -j .text /tmp/hold_c.o /tmp/hold_c.bin
!   python3 -c "print(open('/tmp/hold_c.bin','rb').read()[2:60].hex())"
! The file starts at 0x8c01341c, so PC-relative literal loads see the real 4-byte
! alignment; .org puts the branch targets and the literal at their real offsets.
	.text
	.global _start
_start:
	.short	0		! 0x8c01341c (not patched; keeps 4-byte alignment true)
	mov.l	@r15,r2		! per
	mov.l	@(8,r2),r1	! on
	not	r1,r3
	mov.l	r3,@(12,r2)	! off = ~on (the negative-logic path reads it)
	mov.l	flagp,r0	! existing literal: &logic-mode flag
	mov.l	@r0,r0
	tst	r0,r0
	bf	neg		! negative logic: unchanged path
	mov	r1,r0
	and	#1,r0		! C (PDD_DGT_TC)
	shll8	r0
	shll	r0		! -> bit 9, Y (PDD_DGT_TY)
	or	r0,r1
	mov.l	r1,@(8,r2)	! on |= C << 9
	not	r1,r3
	mov.l	r3,@(12,r2)	! off = ~on
	mov.l	@(44,r2),r0	! previous on
	xor	r1,r0		! changed bits
	mov.l	r0,@(12,r15)
	mov	r0,r4
	and	r1,r0
	mov.l	r0,@(16,r2)	! press = changed & on
	and	r3,r4
	mov.l	r4,@(20,r2)	! release = changed & off
	bra	join
	nop
	nop
	nop
	nop
	.org	0x8c013458 - 0x8c01341c
neg:
	.org	0x8c013484 - 0x8c01341c
join:
	.org	0x8c013490 - 0x8c01341c
flagp:	.long	0x8c10663c
