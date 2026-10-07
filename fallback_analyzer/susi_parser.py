import re
from typing import Dict, List, Optional, Tuple

from .models import SuSiTarget

class SusiParser:
    """Parses SuSi source and sink lists and converts them to Smali signatures."""

    # Matches: <class.name: return.type method_name(param1,param2)> (PERMISSION:...) <CATEGORY:...>
    # Example: <android.telephony.TelephonyManager: java.lang.String getDeviceId()> (PERMISSION:android.permission.READ_PHONE_STATE) <CATEGORY:TELEPHONY>
    SUSI_REGEX = re.compile(
        r'<([^:]+):\s+([^ ]+)\s+([^\(]+)\((.*?)\)>(?:\s+\(PERMISSION:([^\)]+)\))?(?:\s+<CATEGORY:([^>]+)>)?'
    )

    TYPE_MAP = {
        "void": "V",
        "boolean": "Z",
        "byte": "B",
        "short": "S",
        "char": "C",
        "int": "I",
        "float": "F",
        "double": "D",
        "long": "J"
    }

    @classmethod
    def java_type_to_smali(cls, java_type: str) -> str:
        """Converts a Java type string to a Smali type string."""
        java_type = java_type.strip()
        if not java_type:
            return ""
            
        array_depth = java_type.count("[]")
        base_type = java_type.replace("[]", "")
        
        prefix = "[" * array_depth
        
        if base_type in cls.TYPE_MAP:
            return prefix + cls.TYPE_MAP[base_type]
        else:
            # Object type
            return prefix + "L" + base_type.replace(".", "/") + ";"

    @classmethod
    def parse_line(cls, line: str) -> Optional[SuSiTarget]:
        """Parses a single line of a SuSi list."""
        line = line.strip()
        if not line or line.startswith("%") or line.startswith("//"):
            return None

        match = cls.SUSI_REGEX.search(line)
        if not match:
            return None

        java_class = match.group(1).strip()
        java_return = match.group(2).strip()
        java_method = match.group(3).strip()
        java_params_str = match.group(4).strip()
        permission = match.group(5)
        category = match.group(6)

        smali_class = "L" + java_class.replace(".", "/") + ";"
        smali_return = cls.java_type_to_smali(java_return)
        
        smali_params = []
        if java_params_str:
            for p in java_params_str.split(","):
                smali_params.append(cls.java_type_to_smali(p.strip()))
        
        params_str = "".join(smali_params)
        smali_signature = f"{smali_class}->{java_method}({params_str}){smali_return}"

        return SuSiTarget(
            signature=smali_signature,
            category=category if category else "UNKNOWN",
            permission=permission.strip() if permission else None
        )

    @classmethod
    def parse_file(cls, filepath: str) -> Dict[str, SuSiTarget]:
        """Parses a SuSi file and returns a mapping of smali signature -> SuSiTarget."""
        targets = {}
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                target = cls.parse_line(line)
                if target:
                    targets[target.signature] = target
        return targets
