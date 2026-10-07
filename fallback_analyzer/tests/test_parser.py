import pytest
from fallback_analyzer.susi_parser import SusiParser

def test_java_type_to_smali():
    assert SusiParser.java_type_to_smali("void") == "V"
    assert SusiParser.java_type_to_smali("int") == "I"
    assert SusiParser.java_type_to_smali("boolean") == "Z"
    assert SusiParser.java_type_to_smali("int[]") == "[I"
    assert SusiParser.java_type_to_smali("java.lang.String") == "Ljava/lang/String;"
    assert SusiParser.java_type_to_smali("java.lang.String[]") == "[Ljava/lang/String;"

def test_parse_susi_line():
    line = "<android.telephony.TelephonyManager: java.lang.String getDeviceId()> (PERMISSION:android.permission.READ_PHONE_STATE) <CATEGORY:TELEPHONY>"
    target = SusiParser.parse_line(line)
    assert target is not None
    assert target.signature == "Landroid/telephony/TelephonyManager;->getDeviceId()Ljava/lang/String;"
    assert target.permission == "android.permission.READ_PHONE_STATE"
    assert target.category == "TELEPHONY"

def test_parse_susi_line_no_permission():
    line = "<android.location.Location: double getLatitude()> <CATEGORY:LOCATION>"
    target = SusiParser.parse_line(line)
    assert target is not None
    assert target.signature == "Landroid/location/Location;->getLatitude()D"
    assert target.permission is None
    assert target.category == "LOCATION"

def test_parse_susi_line_with_params():
    line = "<android.location.LocationManager: android.location.Location getLastKnownLocation(java.lang.String)> (PERMISSION:android.permission.ACCESS_FINE_LOCATION) <CATEGORY:LOCATION>"
    target = SusiParser.parse_line(line)
    assert target is not None
    assert target.signature == "Landroid/location/LocationManager;->getLastKnownLocation(Ljava/lang/String;)Landroid/location/Location;"
