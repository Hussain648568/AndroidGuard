import pytest
import os
import tempfile
from fallback_analyzer.manifest import ManifestParser

@pytest.fixture
def manifest_files():
    with tempfile.TemporaryDirectory() as temp_dir:
        json_path = os.path.join(temp_dir, "category_permissions.json")
        with open(json_path, 'w') as f:
            f.write('{"LOCATION": ["android.permission.ACCESS_FINE_LOCATION"]}')
            
        manifest_path = os.path.join(temp_dir, "AndroidManifest.xml")
        xml_content = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="com.test.app">
    <uses-sdk android:targetSdkVersion="30" />
    <uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
    <uses-permission-sdk-23 android:name="android.permission.READ_CONTACTS" />
    <application>
        <activity android:name=".MainActivity" />
        <service android:name="com.test.app.MyService" />
        <receiver android:name=".MyReceiver" />
    </application>
</manifest>
"""
        with open(manifest_path, 'w') as f:
            f.write(xml_content)
            
        yield json_path, manifest_path

def test_manifest_parser(manifest_files):
    json_path, manifest_path = manifest_files
    
    parser = ManifestParser(json_path)
    data = parser.parse(manifest_path)
    
    assert data.package_name == "com.test.app"
    assert data.target_sdk == 30
    assert "android.permission.ACCESS_FINE_LOCATION" in data.permissions
    assert "android.permission.READ_CONTACTS" in data.permissions
    
    assert "Lcom/test/app/MainActivity;" in data.components
    assert "Lcom/test/app/MyService;" in data.components
    assert "Lcom/test/app/MyReceiver;" in data.components

    assert parser.get_required_permissions_for_category("LOCATION") == ["android.permission.ACCESS_FINE_LOCATION"]
    assert parser.get_required_permissions_for_category("UNKNOWN") == []
