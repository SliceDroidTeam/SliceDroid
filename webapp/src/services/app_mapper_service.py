"""
App Mapper Service for SliceDroid Dashboard
Manages app mapping from Android devices using real APK analysis
"""

import json
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

        # Load existing mapping immediately without any delays
        self.load_mapping()

    def load_mapping(self) -> Dict[str, AppInfo]:
        """Load app mapping from file"""
        try:
            if self.mapping_file.exists():
                print(f"Loading mapping from: {self.mapping_file}")
                with open(self.mapping_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                print(f"Found {len(data)} apps in JSON file")
                for pkg, info in data.items():
                    try:
                        # Handle both old and new JSON structures
                        package_name = info.get('package_name', pkg)
                        commercial_name = info.get('commercial_name', pkg)
                        processes = info.get('processes', [pkg])
                        is_running = info.get('is_running', False)

                        # Determine category based on available information
                        category = info.get('category', 'User')  # Use existing category if available
                        if category == 'User':
                            # Try to determine category from package name patterns
                            if any(system_pkg in package_name for system_pkg in [
                                'com.android.', 'com.google.android.', 'android.',
                                'com.samsung.', 'com.sec.', 'com.lge.', 'com.htc.',
                                'com.huawei.', 'com.xiaomi.', 'com.oppo.', 'com.vivo.',
                                'com.oneplus.', 'com.nothing.'
                            ]):
                                category = 'System'

                        self.apps_cache[pkg] = AppInfo(
                            package_name=package_name,
                            commercial_name=commercial_name,
                            category=category,
                            processes=processes,
                            is_running=is_running
                        )
                    except Exception as app_error:
                        print(f"Error loading app {pkg}: {app_error}")

                print(f"Successfully loaded {len(self.apps_cache)} apps from mapping file")
            else:
                print(f"Mapping file not found: {self.mapping_file}")

        except Exception as e:
            print(f"Error loading app mapping: {e}")
            import traceback
            traceback.print_exc()

        return self.apps_cache


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
        """Get process names for app with shortened names"""
        # Try as package name first
        app = self.get_app_by_package(app_identifier)
        if app:
            return self._get_shortened_process_names(app.processes)

        # Then try as commercial name
        app = self.get_app_by_commercial_name(app_identifier)
        if app:
            return self._get_shortened_process_names(app.processes)

        return []

    def _get_shortened_process_names(self, process_names: List[str]) -> List[str]:
        """Convert process names to last 15 characters for trace matching"""
        shortened = []
        for process_name in process_names:
            # Use last 15 characters of process name for trace matching
            shortened_name = process_name[-15:] if len(process_name) > 15 else process_name
            shortened.append(shortened_name)

        return list(set(shortened))  # Remove duplicates

    def get_categories(self) -> List[str]:
        """Get all app categories"""
        categories = set()
        for app in self.apps_cache.values():
            categories.add(app.category)
        return sorted(list(categories))

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

    def force_reload_mapping(self) -> Dict[str, str]:
        """Force reload mapping from file without running device script"""
        try:
            old_count = len(self.apps_cache)
            self.apps_cache.clear()  # Clear existing cache
            self.load_mapping()  # Reload from file
            new_count = len(self.apps_cache)
            
            return {
                "success": True,
                "message": f"Mapping reloaded from file: {old_count} -> {new_count} apps",
                "old_count": old_count,
                "new_count": new_count
            }
        except Exception as e:
            return {"error": f"Failed to reload mapping: {str(e)}"}

    def refresh_mapping_from_device(self, force: bool = False) -> Dict[str, str]:
        """Refresh mapping from connected device"""
        try:
            import subprocess

            # Check if mapping file already exists (unless force is True)
            if self.mapping_file.exists() and not force:
                # Just reload the existing file instead of skipping
                return self.force_reload_mapping()

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

    def get_device_status(self) -> Dict[str, any]:
        """Get device and connection status (fast version without checks)"""
        return {
            "device_connected": self.device_connected,
            "adb_available": True,  # Assume available to avoid subprocess calls
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
        """Get PIDs for app from trace events using process name matching"""
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
        result = {
            "package_name": app.package_name,
            "commercial_name": app.commercial_name,
            "processes": app.processes,
            "is_running": app.is_running
        }

        # Only include category if it exists
        if hasattr(app, 'category') and app.category:
            result["category"] = app.category

        # Only include icon_url if it exists and is not None
        if hasattr(app, 'icon_url') and app.icon_url:
            result["icon_url"] = app.icon_url

        return result