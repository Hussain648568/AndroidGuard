import re
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

class SusiLoader:
    """
    Loads and parses SuSi files, converting Soot Java signatures to Smali signatures.
    """

    PRIMITIVES = {
        'void': 'V',
        'boolean': 'Z',
        'byte': 'B',
        'short': 'S',
        'char': 'C',
        'int': 'I',
        'float': 'F',
        'double': 'D',
        'long': 'J',
    }

    # Matches: <class.name: return_type method_name(param1,param2)> (optional suffixes)
    SOOT_SIG_PATTERN = re.compile(r'^<([^:]+):\s+([^ ]+)\s+([^\(]+)\((.*?)\)>(.*)$')
    
    # Matches: <CATEGORY:SOMETHING>
    CATEGORY_PATTERN = re.compile(r'<CATEGORY:([^>]+)>')

    def __init__(self):
        # Primary index: smali_signature -> dict
        self.sources: Dict[str, Dict[str, str]] = {}
        self.sinks: Dict[str, Dict[str, str]] = {}
        
        # Secondary index: (method_name, descriptor) -> dict
        self.secondary_sources: Dict[Tuple[str, str], Dict[str, str]] = {}
        self.secondary_sinks: Dict[Tuple[str, str], Dict[str, str]] = {}

    def _java_to_smali_type(self, java_type: str) -> str:
        """Converts a Java type string (e.g. java.lang.String[]) to a Smali type ([Ljava/lang/String;)."""
        java_type = java_type.strip()
        if not java_type:
            return ""
        
        array_depth = java_type.count('[]')
        base_type = java_type.replace('[]', '').strip()
        
        prefix = '[' * array_depth
        if base_type in self.PRIMITIVES:
            return prefix + self.PRIMITIVES[base_type]
        else:
            return prefix + 'L' + base_type.replace('.', '/') + ';'

    def load_files(self, filepaths: List[str]):
        """Parses multiple SuSi files and populates the source/sink dictionaries."""
        for filepath in filepaths:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.load_lines(f.readlines(), source_name=filepath)

    def load_lines(self, lines: List[str], source_name: str = "unknown"):
        """Parses a list of lines (useful for testing and generic loading)."""
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            # Ignore blank lines and comments
            if not line or line.startswith('%') or line.startswith('//'):
                continue
            
            self._parse_line(line, source_name, line_num)

    def _parse_line(self, line: str, source_name: str, line_num: int):
        match = self.SOOT_SIG_PATTERN.search(line)
        if not match:
            logger.warning(f"Malformed SuSi line skipped ({source_name}:{line_num}): {line}")
            return

        class_name = match.group(1).strip()
        return_type = match.group(2).strip()
        method_name = match.group(3).strip()
        params_str = match.group(4).strip()
        rest = match.group(5).strip()

        # Extract category if present
        cat_match = self.CATEGORY_PATTERN.search(rest)
        category = cat_match.group(1) if cat_match else "UNKNOWN"

        # Determine if it's a source or sink (or both)
        is_source = "->_SOURCE_" in rest.replace(" ", "") or "-> _SOURCE_" in rest
        is_sink = "->_SINK_" in rest.replace(" ", "") or "-> _SINK_" in rest

        if not is_source and not is_sink:
            # Fallback if there's no explicit -> _SOURCE_ but it has _SOURCE_ keyword
            if "_SOURCE_" in rest:
                is_source = True
            elif "_SINK_" in rest:
                is_sink = True
            else:
                logger.warning(f"Line has no _SOURCE_ or _SINK_ marker ({source_name}:{line_num}): {line}")
                return

        # Convert Java types to Smali
        smali_class = 'L' + class_name.replace('.', '/') + ';'
        smali_return = self._java_to_smali_type(return_type)
        
        smali_params = []
        if params_str:
            for p in params_str.split(','):
                smali_params.append(self._java_to_smali_type(p.strip()))
        
        descriptor = f"({''.join(smali_params)}){smali_return}"
        smali_signature = f"{smali_class}->{method_name}{descriptor}"
        original_soot_signature = f"<{class_name}: {return_type} {method_name}({params_str})>"

        data = {
            "category": category,
            "original_soot_signature": original_soot_signature
        }

        secondary_key = (method_name, descriptor)

        if is_source:
            self.sources[smali_signature] = data
            self.secondary_sources[secondary_key] = data
        if is_sink:
            self.sinks[smali_signature] = data
            self.secondary_sinks[secondary_key] = data

    def get_structures(self) -> Tuple[Dict, Dict]:
        """Returns the primary sources and sinks dictionaries."""
        return self.sources, self.sinks
