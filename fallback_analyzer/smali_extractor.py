import subprocess
import os
import shutil
from typing import List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class ExtractorResult:
    success: bool
    output_dir: Optional[str]
    smali_roots: List[str]
    error_message: Optional[str]

class SmaliExtractor:
    """Handles extracting an APK into Smali files using apktool."""

    def __init__(self, timeout: int = 600, apktool_cmd: str = None):
        self.timeout = timeout
        
        # We will dynamically build the command array
        self.cmd_base = []

        if apktool_cmd:
            self.cmd_base = [apktool_cmd]
        else:
            # Check local tools folder first
            local_jar = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "apktool.jar")
            if os.path.exists(local_jar):
                self.cmd_base = ["java", "-jar", local_jar]
            else:
                self.cmd_base = ["apktool"]

    def _check_apktool(self) -> bool:
        """Checks if apktool is available."""
        if self.cmd_base[0] == "java":
            return True
        return shutil.which(self.cmd_base[0]) is not None

    def extract(self, apk_path: str, output_dir: str) -> ExtractorResult:
        """
        Runs apktool to decode the APK.
        """
        if not self._check_apktool():
            return ExtractorResult(
                success=False, 
                output_dir=None, 
                smali_roots=[], 
                error_message=f"apktool is missing. Tried command: {self.cmd_base}"
            )
        
        # -o: output directory, -f: force overwrite
        cmd = self.cmd_base + ["d", apk_path, "-o", output_dir, "-f"]
        
        try:
            subprocess.run(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                timeout=self.timeout, 
                check=True, 
                text=True
            )
        except subprocess.TimeoutExpired:
            return ExtractorResult(
                success=False, 
                output_dir=None, 
                smali_roots=[], 
                error_message=f"apktool extraction timed out after {self.timeout}s"
            )
        except subprocess.CalledProcessError as e:
            return ExtractorResult(
                success=False, 
                output_dir=None, 
                smali_roots=[], 
                error_message=f"apktool extraction failed with code {e.returncode}: {e.stderr}"
            )
        except Exception as e:
            return ExtractorResult(
                success=False, 
                output_dir=None, 
                smali_roots=[], 
                error_message=f"Unexpected error during apktool extraction: {str(e)}"
            )

        # Extraction successful, find all smali roots (smali, smali_classes2, etc.)
        smali_roots = []
        if os.path.exists(output_dir):
            for entry in os.listdir(output_dir):
                if entry.startswith("smali"):
                    full_path = os.path.join(output_dir, entry)
                    if os.path.isdir(full_path):
                        smali_roots.append(full_path)
                        
        return ExtractorResult(
            success=True, 
            output_dir=output_dir, 
            smali_roots=smali_roots, 
            error_message=None
        )
