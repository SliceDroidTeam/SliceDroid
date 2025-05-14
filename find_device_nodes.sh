#!/bin/sh
set -euo pipefail

# ────── same constants as in <linux/kdev_t.h> ──────
MINORBITS=20
MINORMASK=$(( (1 << MINORBITS) - 1 ))
# ───────────────────────────────────────────────────

out1="rdevs.txt"
: > "$out1"

out2="regular_files.txt"
: > "$out2"

find /dev -mindepth 1 \( -type c -o -type b \) -print0 |
while IFS= read -r -d '' path; do
    name=${path#/dev/}

    # get original hex major:minor
    hex=$(stat -c '%t:%T' "$path")
    maj_hex=${hex%%:*}
    min_hex=${hex##*:}

    maj=$((0x$maj_hex))
    mino=$((0x$min_hex))

    rdev32=$(( (maj << MINORBITS) | (mino & MINORMASK) ))
    maj_extracted=$(( rdev32 >> MINORBITS ))
    min_extracted=$(( rdev32 & MINORMASK ))
    printf '%s %d\n' "$name" "$rdev32"
done |
sort > "$out1"

for path in \
    /data/data/com.android.providers.contacts/databases/contacts2.db \
    /data/data/com.android.providers.telephony/databases/mmssms.db \
    /data/data/com.android.providers.calendar/databases/calendar.db \
    /data/data/com.android.providers.contacts/databases/calllog.db
do
    file="$path"
    # 1) get inode
    ino=$(stat -c '%i' "$file")
    # 2) get the legacy 16-bit packed st_dev
    dev16=$(stat -c '%d' "$file")
    # 3) extract the 8-bit major & minor from that legacy form
    maj=$(( dev16 >> 8 ))
    min=$(( dev16 & 0xFF ))
    # 4) re-pack into the kernel's 32-bit dev_t layout
    dev32=$(( (maj << 20) | min ))
    echo "$file" "$dev32" "$ino"
done |
sort > "$out2"