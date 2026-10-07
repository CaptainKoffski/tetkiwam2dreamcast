#!/bin/bash
# Serial capture over the coder's cable -> build/$DIAG_DIR/<leg>.log (default diag-r5; never overwritten).
# From ../senkosp2dreamcast/scripts/capture_serial.sh (same termios trap: macOS resets
# the port settings when its last fd closes, so fd 3 stays open across stty and read).
# 115200 8N1 = what gdtrace_init programs (KOS scif_init sequence). Start it BEFORE
# booting the disc; ctrl-C when done.
set -euo pipefail
leg="${1:?usage: capture_serial.sh <leg-name> [device] [baud]}"
repo="$(cd "$(dirname "$0")/../.." && pwd)"
dev="${2:-$(ls /dev/cu.usbserial* 2>/dev/null | head -1)}"
baud="${3:-115200}"
[ -n "$dev" ] || { echo "no /dev/cu.usbserial* found -- cable plugged in?" >&2; exit 1; }
log="$repo/build/${DIAG_DIR:-diag-r5}/$leg.log"
mkdir -p "$(dirname "$log")"
[ -e "$log" ] && { echo "refusing to overwrite existing $log" >&2; exit 1; }
if lsof "$dev" >/dev/null 2>&1; then
    echo "port busy -- close whatever holds it (screen?). Holder:" >&2
    lsof "$dev" >&2; exit 1
fi
exec 3< "$dev"
stty -f "$dev" raw "$baud" cs8 -parenb -cstopb clocal
echo "capturing $dev @ $baud -> $log  (ctrl-C to stop)"
exec tee "$log" <&3
