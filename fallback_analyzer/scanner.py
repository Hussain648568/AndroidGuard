import os
import re
import logging
from typing import Dict, Any, Generator, List, Tuple
from multiprocessing import Pool

from fallback_analyzer.config import SKIP_PACKAGES

logger = logging.getLogger(__name__)

INVOKE_PATTERN = re.compile(
    r'invoke-(?:virtual|static|direct|interface|super)(?:/range)?\s+\{[^\}]+\},\s*(L[^;]+;->([^\(]+)(\([^)]*\)[^ ]+))'
)

# Global variables for worker processes to avoid pickling overhead per-file
_worker_sources = {}
_worker_sinks = {}
_worker_sec_sources = {}
_worker_sec_sinks = {}

def _init_worker(sources, sinks, sec_sources, sec_sinks):
    """Initializes global state in each multiprocessing worker."""
    global _worker_sources, _worker_sinks, _worker_sec_sources, _worker_sec_sinks
    _worker_sources = sources
    _worker_sinks = sinks
    _worker_sec_sources = sec_sources
    _worker_sec_sinks = sec_sinks

def _check_hit(target_signature: str, method_name: str, descriptor: str, 
               primary: Dict, secondary: Dict) -> Dict[str, str]:
    if target_signature in primary:
        return {"category": primary[target_signature]["category"], "match_type": "exact"}
    
    sec_key = (method_name, descriptor)
    if sec_key in secondary:
        return {"category": secondary[sec_key]["category"], "match_type": "name_descriptor"}
        
    return {}

def _scan_file_worker(file_path: str) -> List[Dict[str, Any]]:
    """Worker function to scan a single smali file."""
    results = []
    current_class = "UNKNOWN"
    current_method = None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_no, line in enumerate(f, 1):
                line_stripped = line.strip()
                if not line_stripped:
                    continue
                
                if line_stripped.startswith(".class"):
                    parts = line_stripped.split()
                    if len(parts) > 1:
                        current_class = parts[-1]
                elif line_stripped.startswith(".method"):
                    if " native " in line_stripped:
                        results.append({
                            "type": "flag", "class": current_class, 
                            "flag": "native_method", "file": file_path, "line_no": line_no
                        })
                    parts = line_stripped.split()
                    if len(parts) > 1:
                        current_method = parts[-1]
                elif line_stripped.startswith(".end method"):
                    current_method = None
                elif line_stripped.startswith("invoke-"):
                    match = INVOKE_PATTERN.search(line_stripped)
                    if match:
                        target_signature = match.group(1)
                        method_name = match.group(2)
                        descriptor = match.group(3)
                        
                        # Check flags for evasion / dynamic loading
                        if "Ldalvik/system/DexClassLoader;-><init>" in target_signature:
                            results.append({"type": "flag", "class": current_class, "flag": "DexClassLoader", "file": file_path, "line_no": line_no})
                        elif "Ldalvik/system/PathClassLoader;-><init>" in target_signature:
                            results.append({"type": "flag", "class": current_class, "flag": "PathClassLoader", "file": file_path, "line_no": line_no})
                        elif "Ljava/lang/reflect/Method;->invoke" in target_signature:
                            results.append({"type": "flag", "class": current_class, "flag": "reflection", "file": file_path, "line_no": line_no})
                        elif "Ljava/lang/System;->loadLibrary" in target_signature or "Ljava/lang/Runtime;->loadLibrary" in target_signature:
                            results.append({"type": "flag", "class": current_class, "flag": "System.loadLibrary", "file": file_path, "line_no": line_no})
                            
                        # Check sources
                        hit = _check_hit(target_signature, method_name, descriptor, _worker_sources, _worker_sec_sources)
                        if hit:
                            results.append({
                                "type": "hit", "kind": "source", "class": current_class, "method": current_method,
                                "target_signature": target_signature, "category": hit["category"], 
                                "match_type": hit["match_type"], "file": file_path, "line_no": line_no
                            })
                            
                        # Check sinks
                        hit = _check_hit(target_signature, method_name, descriptor, _worker_sinks, _worker_sec_sinks)
                        if hit:
                            results.append({
                                "type": "hit", "kind": "sink", "class": current_class, "method": current_method,
                                "target_signature": target_signature, "category": hit["category"], 
                                "match_type": hit["match_type"], "file": file_path, "line_no": line_no
                            })
    except Exception as e:
        logger.error(f"Error scanning file {file_path}: {e}")
        
    return results

class Scanner:
    """Scans Smali files for SuSi targets and blind spot indicators."""
    
    def __init__(self, sources: Dict, sinks: Dict, sec_sources: Dict, sec_sinks: Dict, skip_packages: List[str] = None):
        self.sources = sources
        self.sinks = sinks
        self.sec_sources = sec_sources
        self.sec_sinks = sec_sinks
        self.skip_packages = skip_packages if skip_packages is not None else SKIP_PACKAGES

    def _should_skip(self, file_path: str) -> bool:
        normalized = file_path.replace("\\", "/")
        for pkg in self.skip_packages:
            if pkg in normalized:
                return True
        return False

    def scan_directories(self, roots: List[str], workers: int = 1) -> Generator[Dict[str, Any], None, None]:
        """
        Yields scan results (hits and flags) from all smali files in the given roots.
        Uses multiprocessing if workers > 1.
        """
        files_to_scan = []
        for root in roots:
            for dirpath, _, filenames in os.walk(root):
                for f in filenames:
                    if f.endswith(".smali"):
                        full_path = os.path.join(dirpath, f)
                        if not self._should_skip(full_path):
                            files_to_scan.append(full_path)
                            
        if workers > 1:
            with Pool(
                processes=workers, 
                initializer=_init_worker, 
                initargs=(self.sources, self.sinks, self.sec_sources, self.sec_sinks)
            ) as pool:
                # imap_unordered streams results as they are ready without holding all in memory
                for file_results in pool.imap_unordered(_scan_file_worker, files_to_scan, chunksize=100):
                    for res in file_results:
                        yield res
        else:
            # Single process mode
            _init_worker(self.sources, self.sinks, self.sec_sources, self.sec_sinks)
            for file_path in files_to_scan:
                for res in _scan_file_worker(file_path):
                    yield res
