from typing import List, Dict, Any
from fallback_analyzer.linker import Finding
from fallback_analyzer.config import SCORER_RULES

class Scorer:
    """Scores linked findings based on confidence rules configured in config.py."""

    def __init__(self, rules: Dict[str, Any] = None):
        self.rules = rules or SCORER_RULES

    def score(self, findings: List[Finding]) -> List[dict]:
        """Evaluates findings and assigns a confidence score."""
        scored_results = []

        for f in findings:
            confidence = "LOW"
            
            src = f.source
            snk = f.sink
            
            # Determine base confidence from config rules
            if f.link_level in self.rules["HIGH"]["link_levels"]:
                if f.permission_granted:
                    if self.rules["HIGH"]["require_exact_match"]:
                        if src.get("match_type") == "exact" and (not snk or snk.get("match_type") == "exact"):
                            confidence = "HIGH"
                        else:
                            # Falls back to medium if name_descriptor match is allowed
                            if self.rules["MEDIUM"]["allow_name_descriptor_match"]:
                                confidence = "MEDIUM"
                    else:
                        confidence = "HIGH"
            elif f.link_level in self.rules["MEDIUM"]["link_levels"]:
                if f.permission_granted:
                    confidence = "MEDIUM"
            else:
                # UNLINKED (source only)
                pass

            # Check if permission is NOT requested but required
            if f.permission_required and not f.permission_granted:
                f.flags.append("likely_library_or_dead_code")
                confidence = "LOW" # Downgrade

            # Prepare final dictionary structure for reporter
            scored_results.append({
                "source": src,
                "sink": snk,
                "link_level": f.link_level,
                "permission_required": f.permission_required,
                "permission_granted": f.permission_granted,
                "flags": f.flags,
                "confidence": confidence,
                "analysis_tier": "heuristic"
            })

        return scored_results
