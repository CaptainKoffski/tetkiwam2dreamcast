! Replacement for 1ST_READ.BIN 0x8c01341e..0x8c013483 (102 bytes), Sega pd library
! per-port update. Two patches (docs/kb/controls.md):
! - Soft reset: A+B+X+Y+Start held on any port masks interrupts (as the game's own
!   exit call at 0x8c0729fc does), turns the MMU off (the game turns it on; DreamShell's
!   ISO Loader catches the exit and reloads DreamShell without turning it off), then jumps
!   to the game's own exit routine (0x8c01c454; BIOS menu).
! - HOLD on X and C: Y's bit (9, HOLD) is also set while X (bit 10; the pad's
!   3-button layout) or the arcade stick's C (bit 0) is held, before off/press/release
!   are derived.
! Both logic paths compute the same press/release in fewer instructions (press/release
! from on and prev directly, without the changed-bits word; the negative-logic path is
! not taken by this game), and the stack scratch word @(12,r15), which nothing outside
! this block reads, is no longer written: that makes the room. build_gdi.py carries the bytes;
! this is their source. Rebuild and print them:
!   B=/opt/toolchains/dc/sh-elf/bin
!   $B/sh-elf-as -little tools/pd_update.s -o /tmp/pd_update.o
!   $B/sh-elf-objcopy -O binary -j .text /tmp/pd_update.o /tmp/pd_update.bin
!   python3 -c "print(open('/tmp/pd_update.bin','rb').read()[2:104].hex())"
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
	bf	neg		! negative logic
	mov	r3,r0		! ~on, before the C alias
	tst	#0x0e,r0	! B 1, A 2, Start 3 all held?
	bf	alias
	shlr8	r0
	tst	#0x06,r0	! Y 9, X 10 held?
	bt	reset
alias:
	mov	r1,r0
	shlr8	r0
	shlr2	r0		! bit 0 = X (PDD_DGT_TX, bit 10)
	or	r1,r0		! bit 0 = X | C (PDD_DGT_TC)
	and	#1,r0
	shll8	r0
	shll	r0		! -> bit 9, Y (PDD_DGT_TY)
	or	r0,r1
	mov.l	r1,@(8,r2)	! on |= (X | C) << 9
	not	r1,r3
	mov.l	r3,@(12,r2)	! off = ~on
	mov.l	@(44,r2),r4	! previous on
	not	r4,r0
	and	r1,r0
	mov.l	r0,@(16,r2)	! press = on & ~prev (= (on ^ prev) & on)
	and	r3,r4
	bra	join
	mov.l	r4,@(20,r2)	! release = off & prev (= (on ^ prev) & off)
reset:
	stc	sr,r0
	or	#0xf0,r0	! IMASK = 15
	ldc	r0,sr
	mov.l	mmucr,r1
	mov	#4,r0
	mov.l	r0,@r1		! MMUCR = TI: TLB invalidated, AT = 0 (MMU off)
	mov.l	exitp,r0
	jmp	@r0		! the game's exit routine; does not return
	nop
	.align	2
exitp:	.long	0x8c01c454
mmucr:	.long	0xff000010
neg:				! t = ~(on ^ prev); press = t | on = on | ~prev; release = t | off = off | prev
	mov.l	@(44,r2),r4
	not	r4,r0
	or	r1,r0
	mov.l	r0,@(16,r2)
	or	r3,r4
	mov.l	r4,@(20,r2)
	.org	0x8c013484 - 0x8c01341c
join:
	.org	0x8c013490 - 0x8c01341c
flagp:	.long	0x8c10663c
