/* gdtrace -- serial log of every GD-ROM BIOS syscall the game makes (diagnostic
 * only, never shipped). Linked at 0x8c004000 (dcload-serial's spot, untouched by
 * the BIOS: dcload-serial target-src/dcload/dcload.x:13). mkdiag.py copies it
 * there at the game's entry, calls gdtrace_init, and points the game's GD
 * syscall stubs at hook_vec instead of the BIOS vector 0x8c0000bc.
 *
 * Output: SCIF 115200 8N1 (KOS kernel/arch/dreamcast/hardware/scif.c scif_init).
 * No mul/div anywhere: the game is Hitachi-ABI code and may expect MACH/MACL kept.
 */
typedef unsigned int u32;
typedef unsigned short u16;
typedef unsigned char u8;
#define R8(a)  (*(volatile u8 *)(a))
#define R16(a) (*(volatile u16 *)(a))
#define SCSMR2  R16(0xffe80000)
#define SCBRR2  R8(0xffe80004)
#define SCSCR2  R16(0xffe80008)
#define SCFTDR2 R8(0xffe8000c)
#define SCFSR2  R16(0xffe80010)
#define SCFCR2  R16(0xffe80018)
#define SCSPTR2 R16(0xffe80020)
#define SCLSR2  R16(0xffe80024)

typedef int (*sysc_t)(int, int, int, int);
#define BIOS_GD_VEC (*(volatile sysc_t *)0x8c0000bc)

int gdtrace_hook(int r4, int r5, int r6, int r7);
__attribute__((section(".vec"))) sysc_t hook_vec = gdtrace_hook;

static int serial_ok = 1;
static u32 n_calls = 0, n_hb = 0;
static int l1_ret = 99, l4_ret = 99, lx_ret[16] = {99,99,99,99,99,99,99,99,99,99,99,99,99,99,99,99};
static u32 l1_s0 = 0, l1_s1 = 0, l4_b0 = 0, l4_b1 = 0, lx_r4[16] = {0};
static u32 stuck_h = 0, stuck_n = 0;


static void putc_(int c)
{
    int t = 800000;                       /* no cable -> give up, as KOS scif_write does */
    if (!serial_ok) return;
    while (!(SCFSR2 & 0x20)) if (--t <= 0) { serial_ok = 0; return; }
    SCFTDR2 = c;
    SCFSR2 &= 0xff9f;
}
static void puts_(const char *s) { while (*s) { if (*s == '\n') putc_('\r'); putc_(*s++); } }
static void hex(u32 v) { int i; for (i = 28; i >= 0; i -= 4) putc_("0123456789abcdef"[(v >> i) & 15]); }
static void sp_hex(u32 v) { putc_(' '); hex(v); }

/* GD-ROM (G1 ATA) registers, read-only ones without side effects: never the data
 * port (0x80, consumes data) or status (0x9c, clears the IRQ) -- KOS cdrom.c/g1ata.c. */
#define GDREG(o) (*(volatile u8 *)(0xa05f7000 + (o)))
static void gd_regs(void)
{
    puts_(" alt"); sp_hex(GDREG(0x18)); puts_(" err"); sp_hex(GDREG(0x84));
    puts_(" ir"); sp_hex(GDREG(0x88)); puts_(" sn"); sp_hex(GDREG(0x8c));
    puts_(" bc"); sp_hex(GDREG(0x90) | (GDREG(0x94) << 8));
}

void gdtrace_init(void)
{
    volatile int i;
    SCSCR2 = 0;
    SCFCR2 = 0x06;
    SCSMR2 = 0;                             /* 8N1, P0/1 */
    SCBRR2 = 12;                            /* 50 MHz / (32 * 115200) - 1 */
    for (i = 0; i < 800000; i++) ;
    SCFCR2 = 0x40;
    SCSPTR2 = 0;
    (void)SCFSR2; SCFSR2 = 0x60;
    (void)SCLSR2; SCLSR2 = 0;
    SCSCR2 = 0x30;
    puts_("\nGDTRACE v2 up, bios gd vec");
    sp_hex((u32)BIOS_GD_VEC);
    puts_("\n");
}

int gdtrace_hook(int r4, int r5, int r6, int r7)
{
    sysc_t real = BIOS_GD_VEC;
    u32 f = (u32)r7 & 15, p0 = 0, p1 = 0, p2 = 0, p3 = 0;
    int ret;
    if (f == 0 && r5) { u32 *p = (u32 *)r5; p0 = p[0]; p1 = p[1]; p2 = p[2]; p3 = p[3]; }
    if (f == 10 && r4) { u32 *p = (u32 *)r4; p0 = p[0]; p1 = p[1]; p2 = p[2]; p3 = p[3]; }
    ret = real(r4, r5, r6, r7);
    n_calls++;
    if (f == 0) {                           /* SEND_COMMAND: r4 = cmd, r5 = params */
        puts_("SEND cmd"); sp_hex(r4); sp_hex(p0); sp_hex(p1); sp_hex(p2); sp_hex(p3);
        puts_(" -> h"); sp_hex(ret); puts_("\n");
    } else if (f == 1) {                    /* CHECK_COMMAND: r4 = handle, r5 = status[4] */
        u32 *s = (u32 *)r5, s0 = s ? s[0] : 0, s1 = s ? s[1] : 0;
        if (ret == 1 && (u32)r4 == stuck_h) {         /* same command still processing */
            stuck_n++;
            if (stuck_n == 1000000 || stuck_n == 4000000) {
                puts_("STUCK h"); sp_hex(r4); puts_(" polls"); sp_hex(stuck_n);
                if (s) { puts_(" st"); sp_hex(s[0]); sp_hex(s[1]); sp_hex(s[2]); sp_hex(s[3]); }
                gd_regs(); puts_("\n");
            }
        } else { stuck_h = (u32)r4; stuck_n = 0; }
        if (ret != l1_ret || s0 != l1_s0 || s1 != l1_s1) {
            puts_("CHK h"); sp_hex(r4); puts_(" ->"); sp_hex(ret);
            if (s) { puts_(" st"); sp_hex(s[0]); sp_hex(s[1]); sp_hex(s[2]); sp_hex(s[3]); }
            puts_("\n");
            l1_ret = ret; l1_s0 = s0; l1_s1 = s1;
        }
    } else if (f == 4) {                    /* DRIVE_STATUS: r4 = buf[2] (status, disc type) */
        u32 *b = (u32 *)r4, b0 = b ? b[0] : 0, b1 = b ? b[1] : 0;
        if (ret != l4_ret || b0 != l4_b0 || b1 != l4_b1) {
            puts_("DRV ->"); sp_hex(ret); puts_(" st"); sp_hex(b0); sp_hex(b1); puts_("\n");
            l4_ret = ret; l4_b0 = b0; l4_b1 = b1;
        }
    } else if (f == 10) {                   /* SECTOR_MODE: r4 = params[4] */
        puts_("MODE"); sp_hex(p0); sp_hex(p1); sp_hex(p2); sp_hex(p3); puts_(" ->"); sp_hex(ret); puts_("\n");
    } else if (f != 2) {                    /* everything but EXEC_SERVER, on change */
        if (ret != lx_ret[f] || (u32)r4 != lx_r4[f]) {
            puts_("F"); sp_hex(f); puts_(" r4"); sp_hex(r4); puts_(" r5"); sp_hex(r5); puts_(" ->"); sp_hex(ret); puts_("\n");
            lx_ret[f] = ret; lx_r4[f] = (u32)r4;
        }
    }
    if (n_calls - n_hb >= 20000) { n_hb = n_calls; puts_("HB"); sp_hex(n_calls); puts_("\n"); }
    return ret;
}
