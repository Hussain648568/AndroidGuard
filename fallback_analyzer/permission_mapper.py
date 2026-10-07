import os
import re
from typing import Dict, List
from fallback_analyzer.susi_loader import SusiLoader

class PermissionMapper:
    """Parses Axplorer mapping files to map exact Smali signatures to Android Permissions."""

    def __init__(self):
        self.signature_to_permissions: Dict[str, List[str]] = {}
        # We reuse SusiLoader's logic to convert Java types to Smali types
        self.loader = SusiLoader()

    def load_axplorer_files(self, filepaths: List[str]):
        """Loads multiple Axplorer files (e.g. framework-map and sdk-map)."""
        for fp in filepaths:
            self._load_file(fp)

    def _load_file(self, filepath: str):
        if not os.path.exists(filepath):
            return
            
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or '::' not in line:
                    continue
                
                parts = line.split('::')
                if len(parts) != 2:
                    continue
                    
                method_part = parts[0].strip()
                permission = parts[1].strip()
                
                # Parse method_part: class.method(params)returntype
                # E.g.: android.hardware.location.ActivityRecognitionHardware.flush()boolean
                match = re.match(r'^(.*?)\.([^\.\(]+)\((.*?)\)(.*?)$', method_part)
                if not match:
                    continue
                    
                java_class = match.group(1).strip()
                method_name = match.group(2).strip()
                params_str = match.group(3).strip()
                return_type = match.group(4).strip()
                
                smali_class = 'L' + java_class.replace('.', '/') + ';'
                smali_return = self.loader._java_to_smali_type(return_type)
                
                smali_params = []
                if params_str:
                    for p in params_str.split(','):
                        smali_params.append(self.loader._java_to_smali_type(p.strip()))
                
                smali_sig = f"{smali_class}->{method_name}({''.join(smali_params)}){smali_return}"
                
                if smali_sig not in self.signature_to_permissions:
                    self.signature_to_permissions[smali_sig] = []
                if permission not in self.signature_to_permissions[smali_sig]:
                    self.signature_to_permissions[smali_sig].append(permission)

    def get_permissions_for_signature(self, smali_sig: str) -> List[str]:
        """Returns a list of required permissions for the given Smali signature."""
        return self.signature_to_permissions.get(smali_sig, [])
