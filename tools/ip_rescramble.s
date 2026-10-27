! CDI only: hook in mkdcdisc's IP.BIN bootstrap, at 0x8c00e200 (IP.BIN 0x6200, a zero
! run up to 0x8000). The CDI stores 1ST_READ.BIN unscrambled, as scene binhack CDIs do,
! because DreamShell's ISO Loader loads a Katana binary as is: it unscrambles only KOS
! binaries (firmware/isoldr/loader/utils.c:107) and calls anything without a KOS header
! Katana (modules/isoldr/module.c:117-121), so a scrambled one hangs at "Executing...".
! A CD boot, though, unscrambles the file as it loads it, which turns a plain file into
! garbage. So the bootstrap scrambles it back in RAM before entering the game: the KOS
! scramble (Marcus Comstedt's scramble.c, public domain; mkdcdisc
! src/third_party/scramble), seeded with the file size like the BIOS's unscramble.
! scramble(unscramble(x)) == x.
! The bootstrap enters the game with `jsr @r0` through the pointer word at 0x8c00e0ac;
! make_cdi.py points that word at `entry` and fills `size` and `head`. If the first 16 bytes
! are already plain (isoldr's "boot from IP.BIN" mode loads the file itself), the hook
! changes nothing; make_cdi.py asserts that the BIOS's unscramble never leaves them plain.
! Buffers: 0x8c800000 (one chunk, at most 2 MB) and the u16 index table at 0x8ca00000.
! Neither is in use at this point.
! The game is then entered the way the bootstrap enters it: r0 = r4 = 0x8c010000,
! r1-r3 and r5-r14 zero (as the bootstrap left them), and pr, r15, sr, vbr and fpscr
! unchanged. make_cdi.py carries the bytes; this is their source. Rebuild and print them:
!   B=/opt/toolchains/dc/sh-elf/bin
!   $B/sh-elf-as -little tools/ip_rescramble.s -o /tmp/ip_rescramble.o
!   $B/sh-elf-objcopy -O binary -j .text /tmp/ip_rescramble.o /tmp/ip_rescramble.bin
!   python3 -c "print(open('/tmp/ip_rescramble.bin','rb').read().hex())"
! Literals are absolute (.long 0x8c00e2xx): the object is never linked.
	.text
	.global _start
_start:
size:	.long	0		! 0x8c00e200: 1ST_READ.BIN length
head:	.long	0, 0, 0, 0	! 0x8c00e204: its first 16 bytes, plain
	.org	0x20
entry:				! 0x8c00e220
	sts	pr,r8
	mov.l	l_game,r4	! r4 = pos = 0x8c010000
	mov.l	l_head,r0
	mov	r4,r1
	mov	#4,r2
same:	mov.l	@r0+,r3
	mov.l	@r1+,r5
	cmp/eq	r3,r5
	bf	scram
	dt	r2
	bf	same
	bra	out		! already plain
	nop
scram:	mov.l	l_size,r0
	mov.l	@r0,r5		! r5 = bytes left
	extu.w	r5,r6		! r6 = seed = size & 0xffff
	mov.l	l_max,r7	! r7 = chunk = 2 MB
chunk:	cmp/hs	r7,r5		! left >= chunk?
	bf	half
	mov	r7,r9
	shlr2	r9
	shlr2	r9
	shlr	r9		! r9 = n = chunk / 32 slices
	mov.l	l_idx,r11
	mov	#0,r10
	mov	r11,r13
init:	mov.w	r10,@r13	! idx[i] = i
	add	#1,r10
	cmp/hs	r9,r10
	bf.s	init
	add	#2,r13
	mov.l	l_buf,r12	! r12 = out
	mov	r9,r10		! for i = n-1 .. 0
slice:	add	#-1,r10
	mov.w	l_mul,r0	! seed = (seed * 2109 + 9273) & 0x7fff
	mul.l	r0,r6
	sts	macl,r6
	mov.w	l_add,r0
	add	r0,r6
	mov.w	l_mask,r0
	and	r0,r6
	mov.w	l_c000,r0	! rand = (seed + 0xc000) & 0xffff (sign-extended 0xc000:
	add	r6,r0		!   same low 16 bits)
	extu.w	r0,r13
	mul.l	r10,r13		! x = (rand * i) >> 16
	sts	macl,r13
	shlr16	r13
	add	r13,r13
	add	r11,r13		! r13 = &idx[x]
	mov	r10,r1
	add	r1,r1
	add	r11,r1		! r1 = &idx[i]
	mov.w	@r13,r2
	mov.w	@r1,r3
	mov.w	r3,@r13		! swap
	mov.w	r2,@r1
	extu.w	r2,r2		! idx[i]
	shll2	r2
	shll2	r2
	shll	r2
	add	r4,r2		! out <- the 32-byte slice at pos + 32 * idx[i]
	mov	#8,r3
cp:	mov.l	@r2+,r0
	mov.l	r0,@r12
	dt	r3
	bf.s	cp
	add	#4,r12
	tst	r10,r10
	bf	slice
	mov.l	l_buf,r12	! the chunk goes back in place
	mov	r7,r3
	shlr2	r3
back:	mov.l	@r12+,r0
	mov.l	r0,@r4
	dt	r3
	bf.s	back
	add	#4,r4		! pos += chunk
	bra	chunk
	sub	r7,r5		! left -= chunk
half:	shlr	r7
	mov	#32,r0
	cmp/hs	r0,r7
	bt	chunk		! the tail under 32 bytes stays as is
out:	lds	r8,pr
	mov	#0,r1
	mov	r1,r2
	mov	r1,r3
	mov	r1,r5
	mov	r1,r6
	mov	r1,r7
	mov	r1,r8
	mov	r1,r9
	mov	r1,r10
	mov	r1,r11
	mov	r1,r12
	mov	r1,r13
	mov	r1,r14
	mov.l	l_game,r0
	jmp	@r0
	mov	r0,r4
	.align	2
l_game:	.long	0x8c010000
l_head:	.long	0x8c00e204
l_size:	.long	0x8c00e200
l_max:	.long	0x200000
l_idx:	.long	0x8ca00000
l_buf:	.long	0x8c800000
l_mul:	.short	2109
l_add:	.short	9273
l_mask:	.short	0x7fff
l_c000:	.short	0xc000
