#!/usr/bin/env python3
"""
SliceDroid App Mapper
Συνδέει commercial app names με package names και process names για Android tracking.
"""

import subprocess
import os
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class AndroidAppMapper:
    def __init__(self, temp_dir: str = "downloaded_apks", aapt_path: str = "aapt"):
        self.temp_dir = Path(temp_dir)
        self.aapt_path = aapt_path
        self.package_to_label = {}
        self.package_to_processes = {}
        self.popular_apps_mapping = self._load_popular_apps_db()
        
    def _load_popular_apps_db(self) -> Dict[str, Dict[str, str]]:
        """Βάση δεδομένων με δημοφιλείς εφαρμογές"""
        return {
            # Social Media
            "com.facebook.katana": {
                "commercial_name": "Facebook",
                "category": "Social",
                "common_processes": ["com.facebook.katana"]
            },
            "com.facebook.orca": {
                "commercial_name": "Messenger",
                "category": "Social", 
                "common_processes": ["com.facebook.orca"]
            },
            "com.instagram.android": {
                "commercial_name": "Instagram",
                "category": "Social",
                "common_processes": ["com.instagram.android"]
            },
            "com.whatsapp": {
                "commercial_name": "WhatsApp",
                "category": "Social",
                "common_processes": ["com.whatsapp", "com.whatsapp.w4b"]
            },
            "com.snapchat.android": {
                "commercial_name": "Snapchat", 
                "category": "Social",
                "common_processes": ["com.snapchat.android"]
            },
            "com.twitter.android": {
                "commercial_name": "Twitter (X)",
                "category": "Social", 
                "common_processes": ["com.twitter.android"]
            },
            "com.discord": {
                "commercial_name": "Discord",
                "category": "Social",
                "common_processes": ["com.discord"]
            },
            
            # Communication
            "com.skype.raider": {
                "commercial_name": "Skype",
                "category": "Communication",
                "common_processes": ["com.skype.raider"]
            },
            "us.zoom.videomeetings": {
                "commercial_name": "Zoom",
                "category": "Communication", 
                "common_processes": ["us.zoom.videomeetings"]
            },
            "com.microsoft.teams": {
                "commercial_name": "Microsoft Teams",
                "category": "Communication",
                "common_processes": ["com.microsoft.teams"]
            },
            
            # Entertainment 
            "com.google.android.youtube": {
                "commercial_name": "YouTube",
                "category": "Entertainment",
                "common_processes": ["com.google.android.youtube"]
            },
            "com.netflix.mediaclient": {
                "commercial_name": "Netflix", 
                "category": "Entertainment",
                "common_processes": ["com.netflix.mediaclient"]
            },
            "com.spotify.music": {
                "commercial_name": "Spotify",
                "category": "Entertainment",
                "common_processes": ["com.spotify.music"]
            },
            "com.amazon.avod.thirdpartyclient": {
                "commercial_name": "Prime Video",
                "category": "Entertainment", 
                "common_processes": ["com.amazon.avod.thirdpartyclient"]
            },
            
            # Gaming
            "com.supercell.clashofclans": {
                "commercial_name": "Clash of Clans",
                "category": "Gaming",
                "common_processes": ["com.supercell.clashofclans"]
            },
            "com.king.candycrushsaga": {
                "commercial_name": "Candy Crush Saga", 
                "category": "Gaming",
                "common_processes": ["com.king.candycrushsaga"]
            },
            
            # Banking & Finance
            "com.paypal.android.p2pmobile": {
                "commercial_name": "PayPal",
                "category": "Finance",
                "common_processes": ["com.paypal.android.p2pmobile"]
            },
            
            # Shopping
            "com.amazon.mShop.android.shopping": {
                "commercial_name": "Amazon Shopping",
                "category": "Shopping", 
                "common_processes": ["com.amazon.mShop.android.shopping"]
            },
            
            # Google Apps
            "com.google.android.gm": {
                "commercial_name": "Gmail",
                "category": "Productivity",
                "common_processes": ["com.google.android.gm"] 
            },
            "com.google.android.apps.maps": {
                "commercial_name": "Google Maps",
                "category": "Navigation",
                "common_processes": ["com.google.android.apps.maps"]
            },
            "com.google.android.apps.photos": {
                "commercial_name": "Google Photos", 
                "category": "Photography",
                "common_processes": ["com.google.android.apps.photos"]
            },
            "com.android.chrome": {
                "commercial_name": "Chrome Browser",
                "category": "Browsers",
                "common_processes": ["com.android.chrome"]
            }
        }

    def check_adb_connection(self) -> bool:
        """Ελέγχει αν υπάρχει σύνδεση με ADB"""
        try:
            result = subprocess.run(["adb", "devices"], 
                                  capture_output=True, text=True, timeout=10)
            devices = [line for line in result.stdout.splitlines() 
                      if line.strip() and not line.startswith("List of devices")]
            return len(devices) > 0 and any("device" in line for line in devices)
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def get_installed_packages(self) -> List[str]:
        """Παίρνει λίστα με τα installed packages"""
        try:
            print("[*] Getting installed packages from device...")
            result = subprocess.run(
                ["adb", "shell", "pm", "list", "packages"], 
                capture_output=True, text=True, timeout=30
            )
            packages = [line.split(":")[1].strip() 
                       for line in result.stdout.splitlines() 
                       if line.startswith("package:")]
            print(f"[+] Found {len(packages)} installed packages")
            return packages
        except Exception as e:
            print(f"[!] Error getting packages: {e}")
            return []

    def get_running_processes(self) -> Dict[str, List[str]]:
        """Παίρνει τα τρέχοντα processes και τα συνδέει με packages"""
        try:
            print("[*] Getting running processes...")
            result = subprocess.run(
                ["adb", "shell", "ps", "-A"], 
                capture_output=True, text=True, timeout=20
            )
            
            package_processes = {}
            for line in result.stdout.splitlines()[1:]:  # Skip header
                parts = line.split()
                if len(parts) >= 9:
                    process_name = parts[8]
                    # Αν το process name μοιάζει με package name
                    if "." in process_name and not process_name.startswith("["):
                        # Βρες το βασικό package name
                        base_package = process_name.split(":")[0]
                        if base_package not in package_processes:
                            package_processes[base_package] = []
                        if process_name not in package_processes[base_package]:
                            package_processes[base_package].append(process_name)
            
            print(f"[+] Found {len(package_processes)} packages with running processes")
            return package_processes
        except Exception as e:
            print(f"[!] Error getting processes: {e}")
            return {}

    def get_app_label_from_apk(self, package_name: str) -> Optional[str]:
        """Παίρνει το application label από το APK"""
        try:
            # Check if device is still connected
            if not self.check_adb_connection():
                print(f"[!] Device disconnected during processing of {package_name}")
                return None
                
            # 1. Πάρε APK path
            result = subprocess.run(
                ["adb", "shell", "pm", "path", package_name],
                capture_output=True, text=True, timeout=15
            )
            
            apk_paths = result.stdout.splitlines()
            base_apk = None
            for line in apk_paths:
                if "base.apk" in line:
                    base_apk = line.split(":")[1].strip()
                    break
            
            if not base_apk:
                return None

            # 2. Pull APK locally
            self.temp_dir.mkdir(exist_ok=True)
            local_apk = self.temp_dir / f"{package_name.replace('.', '_')}_base.apk"
            
            subprocess.run(["adb", "pull", base_apk, str(local_apk)], 
                         check=True, timeout=30)

            # 3. Extract label using aapt
            result = subprocess.run(
                [self.aapt_path, "dump", "badging", str(local_apk)],
                capture_output=True, text=True, timeout=15
            )
            
            for line in result.stdout.splitlines():
                if line.startswith("application-label:"):
                    label = line.split(":", 1)[1].strip().strip("'\"")
                    # Cleanup το local APK
                    local_apk.unlink(missing_ok=True)
                    return label
            
            # Cleanup σε περίπτωση αποτυχίας
            local_apk.unlink(missing_ok=True)
            return None
            
        except Exception as e:
            print(f"[!] Error getting label for {package_name}: {e}")
            return None

    def create_app_mapping(self, limit: Optional[int] = None) -> Dict[str, Dict]:
        """Δημιουργεί mapping από packages σε app info"""
        if not self.check_adb_connection():
            print("[!] No ADB connection found. Using popular apps database only.")
            return self._create_popular_apps_only()

        packages = self.get_installed_packages()
        running_processes = self.get_running_processes()
        
        if limit:
            packages = packages[:limit]
            
        app_mapping = {}
        
        for i, pkg in enumerate(packages, 1):
            print(f"[*] Processing {pkg} ({i}/{len(packages)})...")
            
            app_info = {
                "package_name": pkg,
                "commercial_name": None,
                "category": "Unknown",
                "processes": running_processes.get(pkg, [pkg]),
                "is_popular": pkg in self.popular_apps_mapping,
                "is_running": pkg in running_processes
            }
            
            # Αν είναι γνωστή εφαρμογή, χρησιμοποίησε τη βάση δεδομένων
            if pkg in self.popular_apps_mapping:
                popular_info = self.popular_apps_mapping[pkg]
                app_info.update({
                    "commercial_name": popular_info["commercial_name"],
                    "category": popular_info["category"],
                    "processes": popular_info["common_processes"]
                })
            else:
                # Προσπάθησε να πάρεις το label από το APK
                label = self.get_app_label_from_apk(pkg)
                if label:
                    app_info["commercial_name"] = label
                else:
                    # Fallback: χρησιμοποίησε το τελευταίο μέρος του package name
                    app_info["commercial_name"] = pkg.split(".")[-1].title()
            
            app_mapping[pkg] = app_info
            
        print(f"\n[+] Created mapping for {len(app_mapping)} applications")
        return app_mapping

    def _create_popular_apps_only(self) -> Dict[str, Dict]:
        """Δημιουργεί mapping μόνο για δημοφιλείς εφαρμογές"""
        app_mapping = {}
        for pkg, info in self.popular_apps_mapping.items():
            app_mapping[pkg] = {
                "package_name": pkg,
                "commercial_name": info["commercial_name"], 
                "category": info["category"],
                "processes": info["common_processes"],
                "is_popular": True,
                "is_running": False  # Δεν μπορούμε να το ελέγξουμε χωρίς ADB
            }
        return app_mapping

    def save_mapping_to_file(self, mapping: Dict, filepath: str = "app_mapping.json"):
        """Αποθηκεύει το mapping σε JSON αρχείο"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(mapping, f, indent=2, ensure_ascii=False)
            print(f"[+] Mapping saved to {filepath}")
        except Exception as e:
            print(f"[!] Error saving mapping: {e}")

    def load_mapping_from_file(self, filepath: str = "app_mapping.json") -> Dict:
        """Φορτώνει mapping από JSON αρχείο"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            print(f"[!] Error loading mapping: {e}")
            return {}

    def get_processes_for_app(self, app_identifier: str) -> List[str]:
        """Παίρνει τα process names για μια εφαρμογή (package ή commercial name)"""
        # Ψάξε πρώτα σαν package name
        if app_identifier in self.package_to_processes:
            return self.package_to_processes[app_identifier]
            
        # Ψάξε σαν commercial name
        for pkg, info in self.package_to_processes.items():
            if info.get("commercial_name", "").lower() == app_identifier.lower():
                return info.get("processes", [pkg])
                
        return []

    def search_apps(self, query: str, mapping: Dict) -> List[Dict]:
        """Αναζήτηση εφαρμογών βάσει query"""
        results = []
        query_lower = query.lower()
        
        for pkg, info in mapping.items():
            if (query_lower in pkg.lower() or 
                query_lower in info.get("commercial_name", "").lower() or
                query_lower in info.get("category", "").lower()):
                results.append(info)
                
        return sorted(results, key=lambda x: x.get("is_popular", False), reverse=True)


def main():
    """CLI interface για το App Mapper"""
    import argparse
    
    parser = argparse.ArgumentParser(description="SliceDroid App Mapper")
    parser.add_argument("--limit", type=int, help="Limit number of packages to process")
    parser.add_argument("--output", default="app_mapping.json", help="Output JSON file")
    parser.add_argument("--aapt", default="aapt", help="Path to aapt tool")
    parser.add_argument("--search", help="Search for apps")
    parser.add_argument("--load", help="Load mapping from file")
    
    args = parser.parse_args()
    
    mapper = AndroidAppMapper(aapt_path=args.aapt)
    
    if args.search and args.load:
        # Search mode
        mapping = mapper.load_mapping_from_file(args.load)
        results = mapper.search_apps(args.search, mapping)
        
        print(f"\n=== Search Results for '{args.search}' ===")
        for app in results:
            print(f"📱 {app['commercial_name']} ({app['package_name']})")
            print(f"   Category: {app['category']}")
            print(f"   Processes: {', '.join(app['processes'])}")
            print(f"   Popular: {'✅' if app['is_popular'] else '❌'}")
            print(f"   Running: {'✅' if app['is_running'] else '❌'}")
            print()
    else:
        # Mapping creation mode
        print("🔍 SliceDroid App Mapper")
        print("=" * 50)
        
        mapping = mapper.create_app_mapping(limit=args.limit)
        mapper.save_mapping_to_file(mapping, args.output)
        
        # Στατιστικά
        print(f"\n📊 Statistics:")
        print(f"   Total apps: {len(mapping)}")
        print(f"   Popular apps: {sum(1 for app in mapping.values() if app['is_popular'])}")
        print(f"   Running apps: {sum(1 for app in mapping.values() if app['is_running'])}")
        
        categories = {}
        for app in mapping.values():
            cat = app.get('category', 'Unknown')
            categories[cat] = categories.get(cat, 0) + 1
            
        print(f"\n📂 Categories:")
        for cat, count in sorted(categories.items()):
            print(f"   {cat}: {count}")


if __name__ == "__main__":
    main()