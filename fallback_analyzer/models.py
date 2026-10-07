import dataclasses
from typing import List, Optional, Set, Dict

@dataclasses.dataclass
class MethodSignature:
    """Represents a parsed Smali method signature."""
    class_name: str
    method_name: str
    return_type: str
    parameters: List[str]

    def to_smali(self) -> str:
        """Returns the signature in Smali format."""
        params_str = "".join(self.parameters)
        return f"{self.class_name}->{self.method_name}({params_str}){self.return_type}"

    @classmethod
    def from_smali(cls, smali_sig: str) -> "MethodSignature":
        """Parses a Smali signature (e.g. Ljava/lang/String;->length()I)"""
        # Basic parsing, to be expanded if needed
        try:
            class_name, rest = smali_sig.split("->")
            method_name, rest2 = rest.split("(")
            params_str, return_type = rest2.split(")")
            
            # Simple parameter parsing - assumes well-formed smali
            parameters = []
            i = 0
            while i < len(params_str):
                if params_str[i] == 'L':
                    end = params_str.find(';', i)
                    parameters.append(params_str[i:end+1])
                    i = end + 1
                elif params_str[i] == '[':
                    # array type
                    start = i
                    while params_str[i] == '[':
                        i += 1
                    if params_str[i] == 'L':
                        end = params_str.find(';', i)
                        parameters.append(params_str[start:end+1])
                        i = end + 1
                    else:
                        parameters.append(params_str[start:i+1])
                        i += 1
                else:
                    parameters.append(params_str[i])
                    i += 1
            return cls(class_name, method_name, return_type, parameters)
        except ValueError:
            raise ValueError(f"Invalid smali signature: {smali_sig}")

@dataclasses.dataclass(frozen=True)
class SuSiTarget:
    """A target method (Source or Sink) from SuSi."""
    signature: str # Smali signature
    category: str # e.g., NETWORK, LOCATION
    permission: Optional[str] = None # The Android permission required, if any

@dataclasses.dataclass(frozen=True)
class FindingLocation:
    """Location of a finding within the app."""
    file_path: str
    class_name: str
    method_name: str
    line_number: int

@dataclasses.dataclass
class HeuristicFinding:
    """A potential data leak finding."""
    source: SuSiTarget
    source_location: FindingLocation
    sink: SuSiTarget
    sink_location: FindingLocation
    score: int # Higher score = higher confidence
    flags: List[str] = dataclasses.field(default_factory=list) # e.g. "same_method", "same_class", "permission_corroborated"

@dataclasses.dataclass
class AnalysisReport:
    """Final output of the fallback analyzer."""
    apk_path: str
    status: str # "success", "analysis_incomplete", etc.
    blind_spots: List[str] # List of reasons for incompleteness (e.g., "reflection", "native")
    findings: List[HeuristicFinding]
    skipped_packages: List[str]
