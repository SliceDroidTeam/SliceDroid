#!/usr/bin/env python3
"""
Self-Installing App Mapper for SliceDroid
Automatically installs dependencies and extracts commercial names from APKs
No venv required, works on Windows automatically
"""

import subprocess
import sys
import os
import importlib.util
import tempfile
import json
from pathlib import Path
from typing import Dict, List, Optional

def check_and_install_dependency(package_name, import_name=None):
    """Check if package is installed, install if missing"""
    if import_name is None:
        import_name = package_name

    try:
        spec = importlib.util.find_spec(import_name)
        if spec is None:
            raise ImportError(f"Module {import_name} not found")
        return True
    except ImportError:
        print(f"Installing {package_name}...")
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", package_name, "--user"
            ])
            print(f"[+] {package_name} installed successfully")
            return True
        except subprocess.CalledProcessError:
            print(f"[!] Failed to install {package_name}")
            return False

def auto_setup():
    """Automatically setup all dependencies"""
    print("[*] Checking dependencies...")
    return check_and_install_dependency("androguard", "androguard")

# Auto-setup when imported
if auto_setup():
    try:
        from androguard.core.apk import APK
        ANDROGUARD_AVAILABLE = True
    except ImportError:
        ANDROGUARD_AVAILABLE = False
else:
    ANDROGUARD_AVAILABLE = False

class AppMapper:
    def __init__(self):
        pass

    def check_adb_available(self) -> bool:
        """Check if ADB is available"""
        try:
            subprocess.run(["adb", "version"], capture_output=True, timeout=5)
            return True
        except:
            return False

    def check_device_connected(self) -> bool:
        """Check if Android device is connected"""
        try:
            result = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=10)
            lines = [line for line in result.stdout.splitlines()
                    if line.strip() and not line.startswith("List of devices")]
            return any("device" in line and "offline" not in line for line in lines)
        except:
            return False

    def get_installed_packages(self, user_apps_only=True) -> List[str]:
        """Get list of installed packages from device"""
        try:
            cmd = ["adb", "shell", "pm", "list", "packages"]
            if user_apps_only:
                cmd.append("-3")  # Third-party packages only

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            packages = [line.split(":")[1].strip()
                       for line in result.stdout.splitlines()
                       if line.startswith("package:")]
            return packages
        except Exception as e:
            print(f"Error getting packages: {e}")
            return []

    def get_app_label(self, package_name: str) -> Optional[str]:
        """Extract commercial name from APK using androguard"""
        if not ANDROGUARD_AVAILABLE:
            return None

        temp_apk = None
        try:
            # Get APK path from device
            result = subprocess.run(
                ["adb", "shell", "pm", "path", package_name],
                capture_output=True, text=True, timeout=10
            )

            if result.returncode != 0:
                return None

            # Find APK path
            device_apk_path = None
            for line in result.stdout.splitlines():
                if line.startswith("package:"):
                    device_apk_path = line.split(":", 1)[1].strip()
                    break

            if not device_apk_path:
                return None

            # Pull APK to temporary file
            temp_apk = tempfile.NamedTemporaryFile(suffix=".apk", delete=False)
            temp_apk.close()

            pull_result = subprocess.run(
                ["adb", "pull", device_apk_path, temp_apk.name],
                capture_output=True, timeout=30
            )

            if pull_result.returncode != 0:
                return None

            # Analyze APK with androguard
            apk = APK(temp_apk.name)
            app_label = apk.get_app_name()

            return app_label if app_label else None

        except Exception as e:
            return None
        finally:
            # Cleanup temporary file
            if temp_apk and os.path.exists(temp_apk.name):
                try:
                    os.unlink(temp_apk.name)
                except:
                    pass

    def _is_commercial_app(self, package_name: str, commercial_name: str) -> bool:
        """Check if this is an app worth including (USER APPS + SPECIFIC GOOGLE APPS ONLY)"""
        package_lower = package_name.lower()



        # ONLY include user apps (non-system apps)
        if not package_lower.startswith(('com.google.', 'com.android.', 'android.')):
            return True

        # Skip ALL system/Google/Android apps
        return False

    def _mapping_matches_device(self, existing_mapping: Dict, device_packages: List[str]) -> bool:
        """Check if existing mapping matches the current device packages"""
        try:
            # Get package names from existing mapping
            mapped_packages = set(existing_mapping.keys())

            # Filter device packages the same way we would for new mapping
            filtered_device_packages = []
            for package in device_packages:
                if self._is_commercial_app(package, "dummy_name"):
                    filtered_device_packages.append(package)

            device_packages_set = set(filtered_device_packages)

            # Check if sets match exactly
            if mapped_packages == device_packages_set:
                print(f"Mapping matches: {len(mapped_packages)} apps in both existing mapping and device")
                return True
            else:
                print(f"Mapping differs: {len(mapped_packages)} in existing, {len(device_packages_set)} on device")
                # Show differences for debugging
                only_in_mapping = mapped_packages - device_packages_set
                only_on_device = device_packages_set - mapped_packages
                if only_in_mapping:
                    print(f"  Only in mapping: {list(only_in_mapping)[:5]}...")
                if only_on_device:
                    print(f"  Only on device: {list(only_on_device)[:5]}...")
                return False

        except Exception as e:
            print(f"Error checking mapping match: {e}")
            return False

    def create_mapping(self, limit: int = 30, include_system: bool = False) -> Dict[str, Dict]:
        """Create mapping from package names to commercial names and processes"""
        mapping = {}

        # Check if existing mapping has the same apps first
        existing_mapping = self.load_mapping("app_mapping.json")
        if existing_mapping:
            print("Checking if existing mapping is still valid...")

        # Check requirements
        if not self.check_adb_available():
            print("ADB not available. Install Android SDK tools.")
            return mapping

        if not self.check_device_connected():
            print("No Android device connected.")
            return mapping

        if not ANDROGUARD_AVAILABLE:
            print("androguard not available. Install failed.")
            return mapping

        # Get ONLY user apps from device (third-party apps)
        print("Getting user apps from device...")
        installed_packages = self.get_installed_packages(user_apps_only=True)

        if not installed_packages:
            print("No packages found on device.")
            return mapping

        # Check if existing mapping contains exactly the same apps
        if existing_mapping and self._mapping_matches_device(existing_mapping, installed_packages):
            print("Existing mapping matches current device apps. Skipping app mapping generation.")
            return existing_mapping

        # Process ALL user apps (no artificial limit needed since we're only getting user apps)
        print(f"Processing {len(installed_packages)} user apps...")

        for i, package in enumerate(installed_packages, 1):
            print(f"[{i}/{len(installed_packages)}] Processing {package}")

            # Try to get commercial name from APK
            commercial_name = self.get_app_label(package)

            if commercial_name:
                print(f"  Found: {commercial_name}")
                mapping[package] = {
                    "package_name": package,
                    "commercial_name": commercial_name,
                    "processes": [package],
                    "is_running": True
                }
            else:
                print(f"  APK analysis failed - skipping {package}")

        print(f"Completed mapping for {len(mapping)} apps")
        return mapping

    def save_mapping(self, mapping: Dict, output_file: str):
        """Save mapping to JSON file"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(mapping, f, indent=2, ensure_ascii=False)
            print(f"Mapping saved to {output_file}")
        except Exception as e:
            print(f"Error saving mapping: {e}")

    def load_mapping(self, input_file: str) -> Dict:
        """Load mapping from JSON file"""
        try:
            if os.path.exists(input_file):
                with open(input_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"Error loading mapping: {e}")
            return {}

    def get_processes_for_apps(self, app_identifiers: List[str]) -> List[str]:
        """Get shortened process names for list of apps"""
        mapping = self.load_mapping("app_mapping.json")

        process_names = []
        for app_id in app_identifiers:
            # Search by package name
            if app_id in mapping:
                if isinstance(mapping[app_id], dict):
                    processes = mapping[app_id].get("processes", [app_id])
                else:
                    processes = [app_id]
                # Convert to shortened names
                shortened_processes = self._get_shortened_process_names(processes)
                process_names.extend(shortened_processes)
            else:
                # Search by commercial name
                found = False
                for package, info in mapping.items():
                    if isinstance(info, dict):
                        if info.get("commercial_name", "").lower() == app_id.lower():
                            processes = info.get("processes", [package])
                            shortened_processes = self._get_shortened_process_names(processes)
                            process_names.extend(shortened_processes)
                            found = True
                            break
                if not found:
                    # Fallback: treat as package name and shorten it
                    shortened = self._get_shortened_process_names([app_id])
                    process_names.extend(shortened)

        return list(set(process_names))

    def _get_shortened_process_names(self, process_names: List[str]) -> List[str]:
        """Convert full package names to shortened process names for trace matching"""
        shortened = []
        for process_name in process_names:
            # Convert com.google.android.apps.nbu.files -> .apps.nbu.files
            # Convert com.android.systemui -> .systemui
            # Convert org.telegram.messenger -> .telegram.messenger
            if '.' in process_name:
                parts = process_name.split('.')
                if len(parts) >= 3:
                    # Take the last 2-3 meaningful parts, skip common prefixes
                    if parts[0] in ['com', 'org'] and parts[1] in ['google', 'android', 'samsung', 'nothing']:
                        if len(parts) > 4:
                            # For long names like com.google.android.apps.nbu.files -> .apps.nbu.files
                            shortened_name = '.' + '.'.join(parts[3:])
                        else:
                            # For com.google.android.contacts -> .contacts
                            shortened_name = '.' + parts[-1]
                    elif parts[0] in ['com', 'org']:
                        # For com.spotify.music -> .spotify.music or org.telegram.messenger -> .telegram.messenger
                        shortened_name = '.' + '.'.join(parts[1:])
                    else:
                        # Keep original if doesn't match patterns
                        shortened_name = process_name
                else:
                    shortened_name = process_name
            else:
                shortened_name = process_name

            shortened.append(shortened_name)
            # Also keep the original for fallback matching
            if shortened_name != process_name:
                shortened.append(process_name)

        return shortened


    def generate_pid_targets(self, selected_apps: List[str], output_file: str = None):
        """Generate pid_targets.txt for eBPF tracing"""
        if not output_file:
            output_file = "pid_targets.txt"

        process_names = self.get_processes_for_apps(selected_apps)

        try:
            with open(output_file, 'w') as f:
                for process in sorted(process_names):
                    f.write(f"{process}\n")

            print(f"Generated {output_file} with {len(process_names)} process targets:")
            for process in sorted(process_names):
                print(f"  - {process}")

            return output_file
        except Exception as e:
            print(f"Error generating pid targets: {e}")
            return None


def main():
    """CLI interface"""
    import argparse

    parser = argparse.ArgumentParser(description="Self-Installing App Mapper")
    parser.add_argument("--create", action="store_true",
                       help="Create app mapping from device")
    parser.add_argument("--limit", type=int, default=100,
                       help="Limit packages to process")
    parser.add_argument("--output", default="app_mapping.json",
                       help="Output file")
    parser.add_argument("--generate-targets", nargs="+",
                       help="Generate pid_targets.txt for apps")
    parser.add_argument("--targets-file", default="pid_targets.txt",
                       help="Targets output file")
    parser.add_argument("--include-system", action="store_true",
                       help="Include system apps")

    args = parser.parse_args()
    mapper = AppMapper()

    if args.generate_targets:
        print(f"Generating process targets for: {args.generate_targets}")
        targets_file = mapper.generate_pid_targets(args.generate_targets, args.targets_file)
        if targets_file:
            print(f"Success! Process targets saved to {targets_file}")

    elif args.create:
        print("Creating app mapping...")
        mapping = mapper.create_mapping(limit=args.limit, include_system=args.include_system)
        mapper.save_mapping(mapping, args.output)

        # Show summary
        total = len(mapping)
        running = sum(1 for app in mapping.values() if app.get("is_running", False))

        print(f"\nSummary:")
        print(f"  Total apps: {total}")
        print(f"  Running apps: {running}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()