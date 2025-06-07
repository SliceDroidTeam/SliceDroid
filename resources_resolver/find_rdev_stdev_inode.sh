#!/bin/sh

# ────── Constants from <linux/kdev_t.h> ──────
MINORBITS=20
MINORMASK=$(( (1 << MINORBITS) - 1 ))
# ──────────────────────────────────────────────

OUT_DEV="/data/local/tmp/rdevs.txt"
OUT_FILES="/data/local/tmp/regular_files.txt"

# Initialize output files
: >"$OUT_DEV"
: >"$OUT_FILES"

# Process all character/block devices under /dev
find /dev -mindepth 1 \( -type c -o -type b \) -print0 |
while IFS= read -r -d '' path; do
    name=${path#/dev/}

    # get original hex major:minor
    hex=$(stat -c '%t:%T' "$path")
    owner=$(stat -c '%U' "$path")
    group_owner=$(stat -c '%G' "$path")
    maj_hex=${hex%%:*}
    min_hex=${hex##*:}

    maj=$((0x$maj_hex))
    mino=$((0x$min_hex))

    rdev32=$(( (maj << MINORBITS) | (mino & MINORMASK) ))
    printf '%s %d %s %s\n' "$name" "$rdev32" "$owner" "$group_owner"
done |
sort > "$OUT_DEV"

# Select database paths depending on manufacturer
manufacturer=$(getprop ro.product.manufacturer)
if [ "$manufacturer" = "Samsung" ]; then
    db_paths=(
        "/data/data/com.samsung.android.providers.contacts/databases/contacts2.db"
        "/data/data/com.samsung.android.providers.telephony/databases/mmssms.db"
        "/data/data/com.samsung.android.providers.calendar/databases/calendar.db"
        "/data/data/com.samsung.android.providers.contacts/databases/calllog.db"
    )
else
    db_paths=(
        "/data/data/com.android.providers.contacts/databases/contacts2.db"
        "/data/data/com.android.providers.telephony/databases/mmssms.db"
        "/data/data/com.android.providers.calendar/databases/calendar.db"
        "/data/data/com.android.providers.contacts/databases/calllog.db"
    )
fi

for file in "${db_paths[@]}"; do
    
        # 1) get inode
        ino=$(stat -c '%i' "$file")
        
        # 2) get full major:minor in hex, use %d:%D because
        #they are not character/block device special files
        hex=$(stat -c '%d:%D' "$file")

        # 3) split into hex‐major and hex‐minor
        maj_hex=${hex%%:*}
        min_hex=${hex##*:}
        maj=$((0x$maj_hex))
        mino=$((0x$min_hex))

        # 4) pack into 32-bit dev_t
        dev32=$(( (maj << MINORBITS) | (mino & MINORMASK) ))

        # 5) emit file, dev32, inode
        printf '%s %d %s\n' "$file" "$dev32" "$ino"

done |
sort >"$OUT_FILES"

echo "Wrote device mapping to $OUT_DEV"
echo "Wrote file mapping   to $OUT_FILES"