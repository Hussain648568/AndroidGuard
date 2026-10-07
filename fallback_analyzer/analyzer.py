import os
import tempfile
import shutil
from typing import Dict, List, Set, Tuple
import dataclasses

from .config import Config
from .models import SuSiTarget, HeuristicFinding, AnalysisReport
from .apk_extractor import ApkExtractor
from .susi_parser import SusiParser
from .manifest_parser import ManifestParser
from .smali_scanner import SmaliScanner

class Analyzer:
    """Orchestrates the fallback static analysis process."""

    def __init__(self, apk_path: str, susi_sources_path: str, susi_sinks_path: str):
        self.apk_path = apk_path
        self.susi_sources_path = susi_sources_path
        self.susi_sinks_path = susi_sinks_path

    def analyze(self) -> AnalysisReport:
        # Load SuSi lists
        sources = SusiParser.parse_file(self.susi_sources_path)
        sinks = SusiParser.parse_file(self.susi_sinks_path)

        # Create a temporary directory for extraction
        temp_dir = tempfile.mkdtemp(prefix="fallback_analyzer_")
        
        try:
            # 1. Extract APK
            extractor = ApkExtractor()
            success = extractor.extract(self.apk_path, temp_dir)
            
            if not success:
                return AnalysisReport(
                    apk_path=self.apk_path,
                    status="extraction_failed",
                    blind_spots=[],
                    findings=[],
                    skipped_packages=list(Config.DEFAULT_SKIP_PACKAGES)
                )

            # 2. Parse Manifest for permissions
            manifest_path = os.path.join(temp_dir, "AndroidManifest.xml")
            permissions = ManifestParser.get_permissions(manifest_path)

            # 3. Scan Smali files
            scanner = SmaliScanner(sources, sinks)
            scanner.scan_directory(temp_dir)

            # 4. Link Sources and Sinks
            findings = self._link_findings(scanner.found_sources, scanner.found_sinks, permissions)

            # 5. Format Report
            status = "success" if not scanner.blind_spots_found else "analysis_incomplete"
            
            return AnalysisReport(
                apk_path=self.apk_path,
                status=status,
                blind_spots=list(scanner.blind_spots_found),
                findings=findings,
                skipped_packages=list(Config.DEFAULT_SKIP_PACKAGES)
            )

        finally:
            # Cleanup temp directory
            shutil.rmtree(temp_dir, ignore_errors=True)

    def _link_findings(self, found_sources, found_sinks, permissions: Set[str]) -> List[HeuristicFinding]:
        """Links sources and sinks based on heuristic rules."""
        findings = []

        # Filter sources by corroborating permissions
        valid_sources = []
        for source, loc in found_sources:
            if source.permission and source.permission not in permissions:
                # Permission not declared, likely dead code or caught exception
                continue
            valid_sources.append((source, loc))

        # Basic Structural Linking: N^2 comparison
        # To avoid O(N^2) explosion, we group by class/method first.
        # But for heuristic matching, let's just do a pairwise match for now,
        # scoring based on proximity.
        
        for src, src_loc in valid_sources:
            for snk, snk_loc in found_sinks:
                score = 0
                flags = []

                if src_loc.class_name == snk_loc.class_name and src_loc.method_name == snk_loc.method_name:
                    score = 100
                    flags.append("same_method")
                elif src_loc.class_name == snk_loc.class_name:
                    score = 50
                    flags.append("same_class")
                else:
                    score = 10
                    flags.append("same_app")

                if src.permission:
                    flags.append("permission_corroborated")

                findings.append(HeuristicFinding(
                    source=src,
                    source_location=src_loc,
                    sink=snk,
                    sink_location=snk_loc,
                    score=score,
                    flags=flags
                ))
                
        # Sort by score descending
        findings.sort(key=lambda x: x.score, reverse=True)
        return findings
