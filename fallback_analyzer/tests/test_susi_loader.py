import pytest
import logging
from fallback_analyzer.susi_loader import SusiLoader

def test_primitives():
    loader = SusiLoader()
    line = "<android.telephony.TelephonyManager: int getNetworkType()> -> _SOURCE_"
    loader.load_lines([line])
    
    assert "Landroid/telephony/TelephonyManager;->getNetworkType()I" in loader.sources
    data = loader.sources["Landroid/telephony/TelephonyManager;->getNetworkType()I"]
    assert data["original_soot_signature"] == "<android.telephony.TelephonyManager: int getNetworkType()>"
    assert data["category"] == "UNKNOWN"

def test_arrays():
    loader = SusiLoader()
    line = "<android.hardware.Camera: void setPreviewCallback(byte[],int[])> <CATEGORY:HARDWARE_CONTROL> -> _SINK_"
    loader.load_lines([line])
    
    assert "Landroid/hardware/Camera;->setPreviewCallback([B[I)V" in loader.sinks
    data = loader.sinks["Landroid/hardware/Camera;->setPreviewCallback([B[I)V"]
    assert data["category"] == "HARDWARE_CONTROL"
    assert ("setPreviewCallback", "([B[I)V") in loader.secondary_sinks

def test_object_types_and_void():
    loader = SusiLoader()
    line = "<android.location.LocationManager: void requestLocationUpdates(java.lang.String,long,float,android.location.LocationListener)> -> _SINK_"
    loader.load_lines([line])
    
    expected_sig = "Landroid/location/LocationManager;->requestLocationUpdates(Ljava/lang/String;JFLandroid/location/LocationListener;)V"
    assert expected_sig in loader.sinks
    assert ("requestLocationUpdates", "(Ljava/lang/String;JFLandroid/location/LocationListener;)V") in loader.secondary_sinks

def test_nested_generics_free_object_types():
    # SuSi signatures don't typically include generics in the method signature, just the base types.
    loader = SusiLoader()
    line = "<android.content.Context: java.lang.Object getSystemService(java.lang.String)> (PERMISSION:android.permission.READ_PHONE_STATE) <CATEGORY:SYSTEM_SETTINGS> -> _SOURCE_"
    loader.load_lines([line])
    
    expected_sig = "Landroid/content/Context;->getSystemService(Ljava/lang/String;)Ljava/lang/Object;"
    assert expected_sig in loader.sources
    assert loader.sources[expected_sig]["category"] == "SYSTEM_SETTINGS"

def test_malformed_line_warning(caplog):
    loader = SusiLoader()
    with caplog.at_level(logging.WARNING):
        # Missing angle brackets
        loader.load_lines(["android.telephony.TelephonyManager: int getNetworkType() -> _SOURCE_"])
    
    assert "Malformed SuSi line skipped" in caplog.text
    assert len(loader.sources) == 0

def test_missing_marker_warning(caplog):
    loader = SusiLoader()
    with caplog.at_level(logging.WARNING):
        # Missing -> _SOURCE_ or -> _SINK_
        loader.load_lines(["<android.telephony.TelephonyManager: int getNetworkType()> <CATEGORY:TELEPHONY>"])
    
    assert "Line has no _SOURCE_ or _SINK_ marker" in caplog.text
    assert len(loader.sources) == 0

def test_comments_and_blank_lines():
    loader = SusiLoader()
    lines = [
        "// This is a comment",
        "%",
        "",
        "   ",
        "<android.telephony.TelephonyManager: int getNetworkType()> -> _SOURCE_"
    ]
    loader.load_lines(lines)
    
    assert len(loader.sources) == 1
    assert "Landroid/telephony/TelephonyManager;->getNetworkType()I" in loader.sources
