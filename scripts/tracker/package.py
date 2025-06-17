import subprocess
import os

# === CONFIG ===
AAPT_PATH = "aapt"  # π.χ. "C:\\Android\\build-tools\\34.0.0\\aapt.exe"
TEMP_DIR = "downloaded_apks"

# === ΒΗΜΑ 1: Πάρε installed packages ===
print("[*] Getting installed packages...")
packages_output = subprocess.check_output(
    ["adb", "shell", "pm", "list", "packages"], encoding="utf-8"
)
packages = [line.split(":")[1].strip() for line in packages_output.splitlines()]

# === Δημιούργησε temp dir ===
os.makedirs(TEMP_DIR, exist_ok=True)

# === ΒΗΜΑ 2-5: Loop για κάθε package ===
package_name_to_label = {}

for pkg in packages:
    print(f"[*] Processing {pkg}...")
    try:
        # 1) Πάρε path APK
        apk_paths = subprocess.check_output(
            ["adb", "shell", "pm", "path", pkg], encoding="utf-8"
        ).splitlines()

        # Βρες το base.apk (αν έχει splits)
        base_apk = None
        for line in apk_paths:
            if "base.apk" in line:
                base_apk = line.split(":")[1].strip()
                break
        if not base_apk:
            print(f"[-] No base.apk for {pkg}")
            continue

        # 2) Pull APK τοπικά
        local_apk = os.path.join(TEMP_DIR, f"{pkg.replace('.', '_')}_base.apk")
        subprocess.run(["adb", "pull", base_apk, local_apk], check=True)

        # 3) Run aapt για να πάρεις το application label
        aapt_output = subprocess.check_output(
            [AAPT_PATH, "dump", "badging", local_apk],
            encoding="utf-8",
            errors="ignore"
        )
        label = None
        for line in aapt_output.splitlines():
            if line.startswith("application-label:"):
                label = line.split(":", 1)[1].strip().strip("'")
                break
        if label:
            package_name_to_label[pkg] = label
            print(f"[+] {pkg} => {label}")
        else:
            print(f"[-] Could not find label for {pkg}")

        # 4) Προαιρετικά, σβήσε το APK για να μην γεμίζει ο δίσκος
        os.remove(local_apk)

    except subprocess.CalledProcessError as e:
        print(f"[!] Error processing {pkg}: {e}")

# === ΒΗΜΑ 6: Τύπωσε το τελικό λεξικό ===
print("\n\n=== Final Dictionary ===")
print(package_name_to_label)