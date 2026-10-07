import json
from typing import List, Dict, Any

class Reporter:
    """Formats and exports ONLY high-confidence, definitive findings to JSON."""

    def __init__(self, apk_path: str, output_path: str):
        self.apk_path = apk_path
        self.output_path = output_path

    def generate_report(self, scored_findings: List[Dict[str, Any]], blind_spots: List[Dict[str, Any]]):
        # STRICLY FILTER FOR DEFINITIVE LEAKS ONLY
        # Accept L1, L2, and L3 links WHERE the permission was actively granted.
        # L3 is included because Android often splits single screens into multiple files 
        # for background threads (e.g. MainActivity$1.smali and MainActivity.smali).
        definitive_leaks = []
        
        for f in scored_findings:
            if f["link_level"] in ["L1", "L2", "L3"] and f["permission_granted"] is True:
                definitive_leaks.append(f)

        report = {
            "apk_path": self.apk_path,
            "status": "success" if not blind_spots else "analysis_incomplete",
            "total_raw_findings": len(scored_findings),
            "definitive_leaks_count": len(definitive_leaks),
            "blind_spots": blind_spots,
            "findings": definitive_leaks  # Only output the filtered, reliable leaks
        }

        # Write to JSON
        with open(self.output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=4)
        
        print(f"[+] Report successfully generated at: {self.output_path}")
        print(f"[!] Filtered {len(scored_findings)} raw heuristic hits down to {len(definitive_leaks)} definitive leaks.")
        return report
