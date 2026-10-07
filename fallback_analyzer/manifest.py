import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Set, List, Dict
import os

@dataclass
class ManifestData:
    package_name: str
    target_sdk: int
    permissions: Set[str]
    components: Set[str] # Smali class format, e.g. Lcom/example/MainActivity;

class ManifestParser:
    """Parses AndroidManifest.xml for permissions and components."""
    
    NS = {'android': 'http://schemas.android.com/apk/res/android'}
    
    def parse(self, manifest_path: str) -> ManifestData:
        try:
            tree = ET.parse(manifest_path)
            root = tree.getroot()
        except Exception:
            return ManifestData("", -1, set(), set())
            
        package_name = root.attrib.get('package', '')
        
        permissions = set()
        for elem in root.findall('uses-permission'):
            perm = elem.get(f"{{{self.NS['android']}}}name")
            if perm:
                permissions.add(perm)
        for elem in root.findall('uses-permission-sdk-23'):
            perm = elem.get(f"{{{self.NS['android']}}}name")
            if perm:
                permissions.add(perm)
                
        target_sdk = -1
        uses_sdk = root.find('uses-sdk')
        if uses_sdk is not None:
            target_sdk_str = uses_sdk.get(f"{{{self.NS['android']}}}targetSdkVersion")
            if target_sdk_str and target_sdk_str.isdigit():
                target_sdk = int(target_sdk_str)
                
        components = set()
        app_node = root.find('application')
        if app_node is not None:
            for comp_type in ['activity', 'service', 'receiver', 'provider', 'activity-alias']:
                for node in app_node.findall(comp_type):
                    name = node.get(f"{{{self.NS['android']}}}name")
                    if name:
                        # Convert Java name to Smali class format
                        if name.startswith('.'):
                            full_name = package_name + name
                        elif '.' not in name:
                            full_name = package_name + '.' + name
                        else:
                            full_name = name
                        smali_name = 'L' + full_name.replace('.', '/') + ';'
                        components.add(smali_name)
                        
        return ManifestData(package_name, target_sdk, permissions, components)
