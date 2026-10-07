import argparse
import os
import tempfile
import time

from fallback_analyzer.smali_extractor import SmaliExtractor
from fallback_analyzer.susi_loader import SusiLoader
from fallback_analyzer.manifest import ManifestParser
from fallback_analyzer.scanner import Scanner
from fallback_analyzer.linker import Linker
from fallback_analyzer.scorer import Scorer
from fallback_analyzer.reporter import Reporter
from fallback_analyzer.permission_mapper import PermissionMapper

def main():
    parser = argparse.ArgumentParser(description="Fallback Static Analyzer for Android")
    parser.add_argument("apk", help="Path to the target APK")
    
    # Default to the newly downloaded datasets
    default_susi = os.path.join("datasets", "SourcesAndSinks.txt")
    default_framework = os.path.join("datasets", "framework-map-25.txt")
    default_sdk = os.path.join("datasets", "sdk-map-25.txt")
    
    parser.add_argument("--susi", default=default_susi, help="Path to SuSi combined file")
    parser.add_argument("--axplorer-framework", default=default_framework, help="Path to Axplorer framework map")
    parser.add_argument("--axplorer-sdk", default=default_sdk, help="Path to Axplorer sdk map")
    parser.add_argument("--out", default="report.json", help="Output JSON path")
    parser.add_argument("--workers", type=int, default=1, help="Number of scanner workers")
    args = parser.parse_args()

    start_time = time.time()
    
    # 1. Load SuSi
    print("[*] Loading SuSi definitions...")
    loader = SusiLoader()
    loader.load_files([args.susi])
    
    # 2. Load Axplorer Mappings
    print("[*] Loading Axplorer permission mappings...")
    perm_mapper = PermissionMapper()
    perm_mapper.load_axplorer_files([args.axplorer_framework, args.axplorer_sdk])
    
    # 3. Extract APK
    print(f"[*] Extracting {args.apk}...")
    extractor = SmaliExtractor()
    with tempfile.TemporaryDirectory() as temp_out:
        ext_res = extractor.extract(args.apk, temp_out)
        if ext_res.success:
            print(f"[+] Extracted to {temp_out}")
        else:
            print(f"[-] Extraction failed: {ext_res.error_message}")
            return
            
        # 4. Parse Manifest
        print("[*] Parsing AndroidManifest.xml...")
        manifest_path = os.path.join(temp_out, "AndroidManifest.xml")
        man_parser = ManifestParser()
        manifest_data = man_parser.parse(manifest_path)
        print(f"    - Package: {manifest_data.package_name}")
        print(f"    - Permissions found: {len(manifest_data.permissions)}")
        
        # 5. Scan
        print(f"[*] Scanning Smali files with {args.workers} workers...")
        scanner = Scanner(loader.sources, loader.sinks, loader.secondary_sources, loader.secondary_sinks)
        
        hits = []
        blind_spots = []
        for result in scanner.scan_directories(ext_res.smali_roots, workers=args.workers):
            if result["type"] == "hit":
                hits.append(result)
            elif result["type"] == "flag":
                blind_spots.append(result)
                
        print(f"[+] Found {len(hits)} source/sink hits and {len(blind_spots)} blind spot indicators.")
        
        # 6. Link
        print("[*] Linking sources and sinks...")
        linker = Linker(manifest_data, perm_mapper)
        findings = linker.link(hits)
        
        # 7. Score
        print("[*] Scoring findings...")
        scorer = Scorer()
        scored = scorer.score(findings)
        
        # 8. Report
        reporter = Reporter(args.apk, args.out)
        reporter.generate_report(scored, blind_spots)
        
    print(f"[*] Done in {time.time() - start_time:.2f} seconds.")

if __name__ == "__main__":
    main()
