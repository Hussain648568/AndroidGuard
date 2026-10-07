import xml.etree.ElementTree as ET
from typing import Set
import os

class ManifestParser:
    """Parses AndroidManifest.xml to extract declared permissions."""

    NS = {'android': 'http://schemas.android.com/apk/res/android'}

    @classmethod
    def get_permissions(cls, manifest_path: str) -> Set[str]:
        """Returns a set of permissions declared in the AndroidManifest.xml."""
        permissions = set()
        if not os.path.exists(manifest_path):
            return permissions
            
        try:
            tree = ET.parse(manifest_path)
            root = tree.getroot()
            
            # Find all uses-permission tags
            for elem in root.findall('uses-permission'):
                perm = elem.get(f"{{{cls.NS['android']}}}name")
                if perm:
                    permissions.add(perm)
                    
            # Also check uses-permission-sdk-23
            for elem in root.findall('uses-permission-sdk-23'):
                perm = elem.get(f"{{{cls.NS['android']}}}name")
                if perm:
                    permissions.add(perm)
                    
        except ET.ParseError:
            pass # Handle corrupted manifest gracefully
            
        return permissions
