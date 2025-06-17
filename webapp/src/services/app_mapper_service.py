"""
App Mapper Service για το SliceDroid Dashboard
Διαχειρίζεται την αντιστοίχιση εφαρμογών με process names
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class AppInfo:
    package_name: str
    commercial_name: str
    category: str
    processes: List[str]
    is_popular: bool = False
    is_running: bool = False
    icon_url: Optional[str] = None

class AppMapperService:
    def __init__(self, project_root: Path, auto_connect: bool = True):
        self.project_root = project_root
        self.mapping_file = project_root / "data" / "app_mapping.json"
        self.mapper_script = project_root / "scripts" / "tracker" / "app_mapper.py"
        self.apps_cache = {}
        self.device_connected = False
        
        # Try to load existing mapping first
        self.load_mapping()
        
        # Auto-connect to device on startup if enabled
        if auto_connect:
            self.auto_connect_and_refresh()
        
    def load_mapping(self) -> Dict[str, AppInfo]:
        """Φορτώνει το app mapping από αρχείο"""
        try:
            if self.mapping_file.exists():
                with open(self.mapping_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                for pkg, info in data.items():
                    self.apps_cache[pkg] = AppInfo(
                        package_name=info['package_name'],
                        commercial_name=info['commercial_name'],
                        category=info['category'],
                        processes=info['processes'],
                        is_popular=info.get('is_popular', False),
                        is_running=info.get('is_running', False)
                    )
                print(f"Loaded {len(self.apps_cache)} apps from mapping file")
            else:
                print("No app mapping file found, using default popular apps")
                self._create_default_mapping()
                
        except Exception as e:
            print(f"Error loading app mapping: {e}")
            self._create_default_mapping()
            
        return self.apps_cache

    def _create_default_mapping(self):
        """Δημιουργεί default mapping με δημοφιλείς εφαρμογές"""
        default_apps = {
            "com.facebook.katana": AppInfo(
                package_name="com.facebook.katana",
                commercial_name="Facebook",
                category="Social",
                processes=["com.facebook.katana"],
                is_popular=True
            ),
            "com.facebook.orca": AppInfo(
                package_name="com.facebook.orca", 
                commercial_name="Messenger",
                category="Social",
                processes=["com.facebook.orca"],
                is_popular=True
            ),
            "com.whatsapp": AppInfo(
                package_name="com.whatsapp",
                commercial_name="WhatsApp", 
                category="Social",
                processes=["com.whatsapp"],
                is_popular=True
            ),
            "com.instagram.android": AppInfo(
                package_name="com.instagram.android",
                commercial_name="Instagram",
                category="Social", 
                processes=["com.instagram.android"],
                is_popular=True
            ),
            "com.google.android.youtube": AppInfo(
                package_name="com.google.android.youtube",
                commercial_name="YouTube",
                category="Entertainment",
                processes=["com.google.android.youtube"],
                is_popular=True
            ),
            "com.spotify.music": AppInfo(
                package_name="com.spotify.music",
                commercial_name="Spotify",
                category="Entertainment",
                processes=["com.spotify.music"],
                is_popular=True
            ),
            "com.android.chrome": AppInfo(
                package_name="com.android.chrome",
                commercial_name="Chrome Browser", 
                category="Browsers",
                processes=["com.android.chrome"],
                is_popular=True
            ),
            "com.google.android.gm": AppInfo(
                package_name="com.google.android.gm",
                commercial_name="Gmail",
                category="Productivity", 
                processes=["com.google.android.gm"],
                is_popular=True
            )
        }
        self.apps_cache = default_apps

    def auto_connect_and_refresh(self):
        """Αυτόματη σύνδεση με ADB και refresh στην εκκίνηση"""
        print("[*] Auto-connecting to ADB device...")
        
        # Check if ADB is available
        if not self._check_adb_available():
            print("[!] ADB not found in PATH")
            return
            
        # Try to connect to device
        if self._try_adb_connection():
            print("[+] ADB device connected successfully")
            self.device_connected = True
            
            # Check if we have a recent mapping (less than 24 hours old)
            if self._is_mapping_recent():
                print("[*] Using recent app mapping from cache")
                return
                
            # Refresh mapping from device in background
            print("[*] Refreshing app mapping from device...")
            self._background_refresh()
        else:
            print("[!] No ADB device found or connected")

    def _check_adb_available(self) -> bool:
        """Ελέγχει αν το ADB είναι διαθέσιμο"""
        try:
            result = subprocess.run(["adb", "version"], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _try_adb_connection(self) -> bool:
        """Προσπαθεί να συνδεθεί με ADB device"""
        try:
            # Start ADB server if not running
            subprocess.run(["adb", "start-server"], 
                         capture_output=True, timeout=10)
            
            # Check for devices
            result = subprocess.run(["adb", "devices"], 
                                  capture_output=True, text=True, timeout=10)
            
            devices = [line for line in result.stdout.splitlines() 
                      if line.strip() and not line.startswith("List of devices")]
            
            connected_devices = [line for line in devices if "device" in line and "offline" not in line]
            
            if connected_devices:
                print(f"[+] Found {len(connected_devices)} connected device(s)")
                return True
            else:
                print("[!] No devices connected or authorized")
                return False
                
        except subprocess.TimeoutExpired:
            print("[!] ADB connection timeout")
            return False
        except Exception as e:
            print(f"[!] ADB connection error: {e}")
            return False

    def _is_mapping_recent(self) -> bool:
        """Ελέγχει αν το mapping είναι πρόσφατο (< 24 ώρες)"""
        try:
            if not self.mapping_file.exists():
                return False
                
            import time
            file_age = time.time() - self.mapping_file.stat().st_mtime
            return file_age < (24 * 60 * 60)  # 24 hours in seconds
            
        except Exception:
            return False

    def _background_refresh(self):
        """Ανανεώνει το mapping στο background"""
        import threading
        
        def refresh_worker():
            try:
                result = self._quick_device_refresh()
                if result.get('success'):
                    print(f"[+] Background refresh completed: {result.get('message', '')}")
                else:
                    print(f"[!] Background refresh failed: {result.get('error', '')}")
            except Exception as e:
                print(f"[!] Background refresh error: {e}")
        
        # Start refresh in background thread
        refresh_thread = threading.Thread(target=refresh_worker, daemon=True)
        refresh_thread.start()

    def _quick_device_refresh(self) -> Dict[str, str]:
        """Γρήγορη ανανέωση από συσκευή (περιορισμένος αριθμός apps)"""
        try:
            if not self.mapper_script.exists():
                return {"error": "App mapper script not found"}
                
            # Create data directory if needed
            self.mapping_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Run script with smaller limit for faster startup
            result = subprocess.run([
                "python3", str(self.mapper_script),
                "--output", str(self.mapping_file),
                "--limit", "30"  # Smaller limit for faster startup
            ], capture_output=True, text=True, timeout=60)  # Shorter timeout
            
            if result.returncode == 0:
                # Reload mapping
                self.load_mapping()
                return {
                    "success": True,
                    "message": f"Quick refresh completed with {len(self.apps_cache)} apps"
                }
            else:
                return {"error": f"Script failed: {result.stderr}"}
                
        except subprocess.TimeoutExpired:
            return {"error": "Quick refresh timed out"}
        except Exception as e:
            return {"error": f"Quick refresh failed: {str(e)}"}

    def get_all_apps(self, category: Optional[str] = None) -> List[AppInfo]:
        """Παίρνει όλες τις εφαρμογές, προαιρετικά φιλτραρισμένες ανά κατηγορία"""
        apps = list(self.apps_cache.values())
        
        if category:
            apps = [app for app in apps if app.category.lower() == category.lower()]
            
        # Ταξινομεί με τις δημοφιλείς πρώτα
        return sorted(apps, key=lambda x: (not x.is_popular, x.commercial_name))

    def search_apps(self, query: str) -> List[AppInfo]:
        """Αναζήτηση εφαρμογών"""
        query_lower = query.lower()
        results = []
        
        for app in self.apps_cache.values():
            if (query_lower in app.commercial_name.lower() or
                query_lower in app.package_name.lower() or
                query_lower in app.category.lower()):
                results.append(app)
                
        return sorted(results, key=lambda x: (not x.is_popular, x.commercial_name))

    def get_app_by_package(self, package_name: str) -> Optional[AppInfo]:
        """Παίρνει εφαρμογή από package name"""
        return self.apps_cache.get(package_name)

    def get_app_by_commercial_name(self, commercial_name: str) -> Optional[AppInfo]:
        """Παίρνει εφαρμογή από commercial name"""
        for app in self.apps_cache.values():
            if app.commercial_name.lower() == commercial_name.lower():
                return app
        return None

    def get_processes_for_app(self, app_identifier: str) -> List[str]:
        """Παίρνει process names για εφαρμογή"""
        # Προσπάθησε σαν package name πρώτα
        app = self.get_app_by_package(app_identifier)
        if app:
            return app.processes
            
        # Μετά σαν commercial name
        app = self.get_app_by_commercial_name(app_identifier)
        if app:
            return app.processes
            
        return []

    def get_categories(self) -> List[str]:
        """Παίρνει όλες τις κατηγορίες εφαρμογών"""
        categories = set()
        for app in self.apps_cache.values():
            categories.add(app.category)
        return sorted(list(categories))

    def refresh_mapping_from_device(self) -> Dict[str, str]:
        """Ανανεώνει το mapping από συνδεδεμένη συσκευή"""
        try:
            # Έλεγχος αν υπάρχει το script
            if not self.mapper_script.exists():
                return {"error": "App mapper script not found"}
                
            # Δημιουργία data directory αν δεν υπάρχει
            self.mapping_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Εκτέλεση του script
            result = subprocess.run([
                "python3", str(self.mapper_script),
                "--output", str(self.mapping_file),
                "--limit", "50"  # Περιορισμός για να μην πάρει πάρα πολύ ώρα
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                # Επαναφόρτωση του mapping
                self.load_mapping()
                return {
                    "success": True,
                    "message": f"Mapping updated with {len(self.apps_cache)} apps",
                    "output": result.stdout
                }
            else:
                return {
                    "error": f"Script failed: {result.stderr}",
                    "output": result.stdout
                }
                
        except subprocess.TimeoutExpired:
            return {"error": "Mapping update timed out"}
        except Exception as e:
            return {"error": f"Failed to update mapping: {str(e)}"}

    def get_app_stats(self) -> Dict[str, int]:
        """Παίρνει στατιστικά εφαρμογών"""
        stats = {
            "total_apps": len(self.apps_cache),
            "popular_apps": sum(1 for app in self.apps_cache.values() if app.is_popular),
            "running_apps": sum(1 for app in self.apps_cache.values() if app.is_running),
            "categories": len(self.get_categories())
        }
        
        # Στατιστικά ανά κατηγορία
        category_stats = {}
        for app in self.apps_cache.values():
            cat = app.category
            category_stats[cat] = category_stats.get(cat, 0) + 1
            
        stats["category_breakdown"] = category_stats
        return stats

    def export_process_targets(self, selected_apps: List[str]) -> str:
        """Εξάγει process targets για τις επιλεγμένες εφαρμογές"""
        process_names = []
        
        for app_id in selected_apps:
            processes = self.get_processes_for_app(app_id)
            process_names.extend(processes)
            
        # Αφαίρεση duplicates και ταξινόμηση
        unique_processes = sorted(list(set(process_names)))
        
        # Δημιουργία PID targets file
        targets_file = self.project_root / "scripts" / "tracer" / "config_files" / "pid_targets.txt"
        targets_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(targets_file, 'w') as f:
            for process in unique_processes:
                f.write(f"{process}\n")
                
        return str(targets_file)

    def get_device_status(self) -> Dict[str, any]:
        """Παίρνει στατιστικά συσκευής και σύνδεσης"""
        return {
            "device_connected": self.device_connected,
            "adb_available": self._check_adb_available(),
            "mapping_file_exists": self.mapping_file.exists(),
            "mapping_age_hours": self._get_mapping_age_hours(),
            "last_refresh": self._get_last_refresh_time()
        }
    
    def _get_mapping_age_hours(self) -> Optional[float]:
        """Παίρνει την ηλικία του mapping file σε ώρες"""
        try:
            if not self.mapping_file.exists():
                return None
            import time
            age_seconds = time.time() - self.mapping_file.stat().st_mtime
            return age_seconds / 3600  # Convert to hours
        except Exception:
            return None
    
    def _get_last_refresh_time(self) -> Optional[str]:
        """Παίρνει το χρόνο της τελευταίας ανανέωσης"""
        try:
            if not self.mapping_file.exists():
                return None
            import datetime
            mtime = self.mapping_file.stat().st_mtime
            return datetime.datetime.fromtimestamp(mtime).isoformat()
        except Exception:
            return None

    def to_dict(self, app: AppInfo) -> Dict:
        """Μετατρέπει AppInfo σε dictionary για JSON serialization"""
        return {
            "package_name": app.package_name,
            "commercial_name": app.commercial_name,
            "category": app.category,
            "processes": app.processes,
            "is_popular": app.is_popular,
            "is_running": app.is_running,
            "icon_url": app.icon_url
        }