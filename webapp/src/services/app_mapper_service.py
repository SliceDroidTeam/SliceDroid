"""
App Mapper Service for SliceDroid Dashboard
Manages app mapping from Android devices using real APK analysis
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
    is_running: bool = False
    icon_url: Optional[str] = None

class AppMapperService:
    def __init__(self, project_root: Path, auto_connect: bool = False):
        self.project_root = project_root
        self.mapping_file = project_root / "data" / "app_mapping.json"
        self.mapper_script = project_root / "scripts" / "tracker" / "app_mapper.py"
        self.apps_cache = {}
        self.device_connected = False
        
        # Load existing mapping
        self.load_mapping()
        
    def load_mapping(self) -> Dict[str, AppInfo]:
        """Load app mapping from file"""
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
                        is_running=info.get('is_running', False)
                    )
                print(f"Loaded {len(self.apps_cache)} apps from mapping file")
            # No print when mapping file doesn't exist - it's normal on first run
                
        except Exception as e:
            print(f"Error loading app mapping: {e}")
            
        return self.apps_cache

    def auto_connect_and_refresh(self):
        """Auto-connect to ADB device and refresh on startup"""
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
        """Check if ADB is available"""
        try:
            result = subprocess.run(["adb", "version"], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _try_adb_connection(self) -> bool:
        """Try to connect to ADB device"""
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
        """Check if mapping is recent (< 24 hours)"""
        try:
            if not self.mapping_file.exists():
                return False
                
            import time
            file_age = time.time() - self.mapping_file.stat().st_mtime
            return file_age < (24 * 60 * 60)  # 24 hours in seconds
            
        except Exception:
            return False

    def _background_refresh(self):
        """Refresh mapping in background"""
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
        """Quick refresh from device with limited number of apps"""
        try:
            if not self.mapper_script.exists():
                return {"error": "App mapper script not found"}
                
            # Create data directory if needed
            self.mapping_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Run script with smaller limit for faster startup
            result = subprocess.run([
                "python", str(self.mapper_script),
                "--create",
                "--output", str(self.mapping_file),
                "--limit", "30",  # Smaller limit for faster startup
                "--include-system"
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
        """Get all apps, optionally filtered by category"""
        apps = list(self.apps_cache.values())
        
        if category:
            apps = [app for app in apps if app.category.lower() == category.lower()]
            
        # Sort by commercial name
        return sorted(apps, key=lambda x: x.commercial_name)

    def search_apps(self, query: str) -> List[AppInfo]:
        """Search apps by name, package, or category"""
        query_lower = query.lower()
        results = []
        
        for app in self.apps_cache.values():
            if (query_lower in app.commercial_name.lower() or
                query_lower in app.package_name.lower() or
                query_lower in app.category.lower()):
                results.append(app)
                
        return sorted(results, key=lambda x: x.commercial_name)

    def get_app_by_package(self, package_name: str) -> Optional[AppInfo]:
        """Get app by package name"""
        return self.apps_cache.get(package_name)

    def get_app_by_commercial_name(self, commercial_name: str) -> Optional[AppInfo]:
        """Get app by commercial name"""
        for app in self.apps_cache.values():
            if app.commercial_name.lower() == commercial_name.lower():
                return app
        return None

    def get_processes_for_app(self, app_identifier: str) -> List[str]:
        """Get process names for app"""
        # Try as package name first
        app = self.get_app_by_package(app_identifier)
        if app:
            return app.processes
            
        # Then try as commercial name
        app = self.get_app_by_commercial_name(app_identifier)
        if app:
            return app.processes
            
        return []

    def get_categories(self) -> List[str]:
        """Get all app categories"""
        categories = set()
        for app in self.apps_cache.values():
            categories.add(app.category)
        return sorted(list(categories))

    def refresh_mapping_from_device(self) -> Dict[str, str]:
        """Refresh mapping from connected device"""
        try:
            # Check if script exists
            if not self.mapper_script.exists():
                return {"error": "App mapper script not found"}
                
            # Create data directory if needed
            self.mapping_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Run script
            result = subprocess.run([
                "python", str(self.mapper_script),
                "--create",
                "--output", str(self.mapping_file),
                "--limit", "50",  # Limit to prevent long execution
                "--include-system"
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                # Reload mapping
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
        """Get app statistics"""
        stats = {
            "total_apps": len(self.apps_cache),
            "running_apps": sum(1 for app in self.apps_cache.values() if app.is_running),
            "categories": len(self.get_categories())
        }
        
        # Stats by category
        category_stats = {}
        for app in self.apps_cache.values():
            cat = app.category
            category_stats[cat] = category_stats.get(cat, 0) + 1
            
        stats["category_breakdown"] = category_stats
        return stats

    def export_process_targets(self, selected_apps: List[str]) -> str:
        """Export process targets for selected apps"""
        process_names = []
        
        for app_id in selected_apps:
            processes = self.get_processes_for_app(app_id)
            process_names.extend(processes)
            
        # Remove duplicates and sort
        unique_processes = sorted(list(set(process_names)))
        
        # Create PID targets file
        targets_file = self.project_root / "scripts" / "tracer" / "config_files" / "pid_targets.txt"
        targets_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(targets_file, 'w') as f:
            for process in unique_processes:
                f.write(f"{process}\n")
                
        return str(targets_file)

    def get_device_status(self) -> Dict[str, any]:
        """Get device and connection status"""
        return {
            "device_connected": self.device_connected,
            "adb_available": self._check_adb_available(),
            "mapping_file_exists": self.mapping_file.exists(),
            "mapping_age_hours": self._get_mapping_age_hours(),
            "last_refresh": self._get_last_refresh_time()
        }
    
    def _get_mapping_age_hours(self) -> Optional[float]:
        """Get mapping file age in hours"""
        try:
            if not self.mapping_file.exists():
                return None
            import time
            age_seconds = time.time() - self.mapping_file.stat().st_mtime
            return age_seconds / 3600  # Convert to hours
        except Exception:
            return None
    
    def _get_last_refresh_time(self) -> Optional[str]:
        """Get last refresh time"""
        try:
            if not self.mapping_file.exists():
                return None
            import datetime
            mtime = self.mapping_file.stat().st_mtime
            return datetime.datetime.fromtimestamp(mtime).isoformat()
        except Exception:
            return None

    def get_pids_for_app(self, app_identifier: str, events: List[Dict]) -> List[int]:
        """Get PIDs for app from trace events"""
        process_names = self.get_processes_for_app(app_identifier)
        if not process_names:
            return []
        
        pids = set()
        for event in events:
            event_process = event.get('process', '')
            if event_process in process_names:
                if 'tgid' in event:
                    pids.add(event['tgid'])
        
        return sorted(list(pids))

    def to_dict(self, app: AppInfo) -> Dict:
        """Convert AppInfo to dictionary for JSON serialization"""
        return {
            "package_name": app.package_name,
            "commercial_name": app.commercial_name,
            "category": app.category,
            "processes": app.processes,
            "is_running": app.is_running,
            "icon_url": app.icon_url
        }