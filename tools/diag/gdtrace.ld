/* gdtrace: one flat blob at 0x8c004000, init first, hook vector right after. */
ENTRY(gdtrace_init)
SECTIONS
{
  . = 0x8c004000;
  .blob : {
    *(.text.gdtrace_init) *(.vec) *(.text*) *(.rodata*) *(.data*) *(.bss*) *(COMMON)
    . = ALIGN(4);
  }
  /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
