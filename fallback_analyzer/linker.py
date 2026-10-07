from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from fallback_analyzer.manifest import ManifestData
from fallback_analyzer.permission_mapper import PermissionMapper

@dataclass
class Finding:
    source: Dict[str, Any]
    sink: Optional[Dict[str, Any]]
    link_level: str
    permission_required: List[str]
    permission_granted: bool
    flags: List[str]

class Linker:
    """Links source and sink hits based on structural proximity."""

    def __init__(self, manifest_data: ManifestData, permission_mapper: PermissionMapper, enable_l4: bool = False, max_hops: int = 3):
        self.manifest_data = manifest_data
        self.permission_mapper = permission_mapper
        self.enable_l4 = enable_l4
        self.max_hops = max_hops

    def _get_component_for_class(self, smali_class: str) -> Optional[str]:
        """Returns the manifest component that this class belongs to (handles inner classes)."""
        if smali_class in self.manifest_data.components:
            return smali_class
            
        # Check inner classes, e.g. Lcom/example/MainActivity$1; belongs to Lcom/example/MainActivity;
        for comp in self.manifest_data.components:
            # removing trailing ';' to append '$'
            base_comp = comp[:-1]
            if smali_class.startswith(base_comp + "$"):
                return comp
        return None

    def link(self, hits: List[Dict[str, Any]], call_edges: Dict[str, List[str]] = None) -> List[Finding]:
        """
        Links sources and sinks. 
        call_edges is an optional adjacency list for L4 linking: { 'Lpkg/Cls;->method()V': ['Lpkg/Cls2;->method2()V'] }
        """
        sources = [h for h in hits if h.get("kind") == "source"]
        sinks = [h for h in hits if h.get("kind") == "sink"]
        
        findings = []

        for src in sources:
            best_sink = None
            best_level = "UNLINKED"
            
            # Lookup real permissions needed for this specific method using Axplorer mapping
            req_perms = self.permission_mapper.get_permissions_for_signature(src["target_signature"])
            # granted if no permissions required OR any of the required permissions is in manifest
            granted = (not req_perms) or any(p in self.manifest_data.permissions for p in req_perms)

            src_comp = self._get_component_for_class(src["class"])

            for snk in sinks:
                level = None
                if src["class"] == snk["class"] and src["method"] == snk["method"]:
                    level = "L1"
                elif src["class"] == snk["class"]:
                    level = "L2"
                elif src_comp and src_comp == self._get_component_for_class(snk["class"]):
                    level = "L3"
                elif self.enable_l4 and call_edges:
                    if self._check_l4(src, snk, call_edges):
                        level = "L4"
                
                # We want to keep the "best" link (L1 > L2 > L3 > L4)
                if level:
                    if best_level == "UNLINKED" or level < best_level:
                        best_level = level
                        best_sink = snk

            findings.append(Finding(
                source=src,
                sink=best_sink,
                link_level=best_level,
                permission_required=req_perms,
                permission_granted=granted,
                flags=[]
            ))
            
        return findings

    def _check_l4(self, src: Dict, snk: Dict, edges: Dict[str, List[str]]) -> bool:
        """BFS to find a path from src method to snk method within max_hops."""
        src_method_sig = f"{src['class']}->{src['method']}"
        snk_method_sig = f"{snk['class']}->{snk['method']}"
        
        if src_method_sig not in edges:
            return False
            
        queue = [(src_method_sig, 0)]
        visited = set([src_method_sig])
        
        while queue:
            curr, depth = queue.pop(0)
            if curr == snk_method_sig:
                return True
            if depth < self.max_hops:
                for neighbor in edges.get(curr, []):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, depth + 1))
        return False
