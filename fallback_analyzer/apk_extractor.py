import subprocess
import tempfile
import os
import shutil
import logging

from .config import Config

logger = logging.getLogger(__name__)

class ApkExtractor:
    """Handles extracting Smali files from an APK using apktool."""

    def __init__(self, apktool_cmd: str = Config.APKTOOL_CMD):
        self.apktool_cmd = apktool_cmd

    def extract(self, apk_path: str, output_dir: str) -> bool:
        """
        Extracts the APK to the given output directory.
        Uses apktool with flags:
        d: decode
        -r: do not decode resources (we only need smali and manifest)
        -f: force overwrite
        -o: output directory
        """
        if not os.path.exists(apk_path):
            logger.error(f"APK not found: {apk_path}")
            return False

        # We actually need the manifest, so we shouldn't use -r if it skips AndroidManifest.xml.
        # Apktool -r skips resources but usually still extracts AndroidManifest.xml.
        # Actually, to be safe and ensure Manifest is fully decoded, we can just omit -r,
        # but to save time, -r does not decode resources, and it just outputs the binary AndroidManifest.xml or keeps it raw?
        # Let's use -s (do not decode sources) - NO we NEED sources.
        # Let's just use `apktool d <apk> -f -o <dir>` to be safe, or just `-r` if it gives decoded manifest.
        # Actually, `apktool d -r` skips decoding resources (res/ and AndroidManifest.xml).
        # We need the decoded manifest. So we cannot use -r.
        # But wait, without -r, apktool might fail on weird resources. Let's just use `apktool d -f -o`
        cmd = [
            self.apktool_cmd,
            "d",
            apk_path,
            "-f",
            "-o", output_dir
        ]

        logger.info(f"Running apktool on {apk_path}...")
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            logger.info("Apktool extraction successful.")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Apktool failed: {e.stderr}")
            return False
