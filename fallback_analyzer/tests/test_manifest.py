import pytest
import os
import tempfile
from fallback_analyzer.manifest import ManifestParser

@pytest.fixture
def manifest_files():
    with tempfile.TemporaryDirectory() as temp_dir:
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
        with open(manifest_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)
            
        yield manifest_path

def test_manifest_parser(manifest_files):
    manifest_path = manifest_files
    
    parser = ManifestParser()
    data = parser.parse(manifest_path)
    
    assert data.package_name == "com.test.app"
    assert data.target_sdk == 30
    assert "android.permission.ACCESS_FINE_LOCATION" in data.permissions
    assert "android.permission.READ_CONTACTS" in data.permissions
    
    assert "Lcom/test/app/MainActivity;" in data.components
    assert "Lcom/test/app/MyService;" in data.components
    assert "Lcom/test/app/MyReceiver;" in data.components
