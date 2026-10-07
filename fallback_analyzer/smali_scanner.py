import os
from typing import Dict, List, Set, Tuple

from .models import FindingLocation, SuSiTarget
from .config import Config

class SmaliScanner:
    """Scans Smali files for source/sink invocations and blind spots."""

    def __init__(self, sources: Dict[str, SuSiTarget], sinks: Dict[str, SuSiTarget], skip_packages: Set[str] = None):
        self.sources = sources
        self.sinks = sinks
        self.skip_packages = skip_packages or Config.DEFAULT_SKIP_PACKAGES
        self.blind_spots_found = set()
        
        self.found_sources: List[Tuple[SuSiTarget, FindingLocation]] = []
        self.found_sinks: List[Tuple[SuSiTarget, FindingLocation]] = []

    def should_skip(self, file_path: str) -> bool:
        """Determines if a file should be skipped based on its path (package)."""
        normalized_path = file_path.replace("\\", "/")
        for pkg in self.skip_packages:
            if pkg in normalized_path:
                return True
        return False

    def scan_directory(self, smali_dir: str):
        """Scans all non-skipped smali files in the given directory."""
        for root, _, files in os.walk(smali_dir):
            for file in files:
                if file.endswith(".smali"):
                    full_path = os.path.join(root, file)
                    if not self.should_skip(full_path):
                        self.scan_file(full_path)

    def scan_file(self, file_path: str):
        """Scans a single smali file."""
        class_name = "UNKNOWN"
        current_method = None
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_number, line in enumerate(f, 1):
                line_stripped = line.strip()
                
                if line_stripped.startswith(".class"):
                    parts = line_stripped.split()
                    if len(parts) > 1:
                        class_name = parts[-1]
                        
                elif line_stripped.startswith(".method"):
                    # e.g., .method public onCreate(Landroid/os/Bundle;)V
                    # Also check for native methods
                    if " native " in line_stripped:
                        self.blind_spots_found.add("native_code")
                        
                    parts = line_stripped.split()
                    if len(parts) > 1:
                        current_method = parts[-1]
                        
                elif line_stripped.startswith(".end method"):
                    current_method = None
                    
                elif line_stripped.startswith("invoke-"):
                    # Check for sources/sinks
                    # Format: invoke-virtual {v0, v1}, Landroid/telephony/TelephonyManager;->getDeviceId()Ljava/lang/String;
                    parts = line_stripped.split(",")
                    if len(parts) > 0:
                        # Extract the signature which is after the last comma (or just split by whitespace)
                        tokens = line_stripped.split()
                        signature = tokens[-1]
                        
                        if signature in self.sources:
                            loc = FindingLocation(file_path, class_name, current_method or "UNKNOWN", line_number)
                            self.found_sources.append((self.sources[signature], loc))
                            
                        if signature in self.sinks:
                            loc = FindingLocation(file_path, class_name, current_method or "UNKNOWN", line_number)
                            self.found_sinks.append((self.sinks[signature], loc))
                            
                        # Check for reflection
                        if "Ljava/lang/reflect/Method;->invoke" in signature:
                            self.blind_spots_found.add("reflection")
                            
                        # Check for dynamic loading
                        if "Ldalvik/system/DexClassLoader;-><init>" in signature or "Ldalvik/system/PathClassLoader;-><init>" in signature:
                            self.blind_spots_found.add("dynamic_loading")
