import pytest
import os
import tempfile
from fallback_analyzer.scanner import Scanner

@pytest.fixture
def smali_workspace():
    """Creates a temporary workspace with smali files for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a skipped library file
        lib_dir = os.path.join(temp_dir, "androidx", "core")
        os.makedirs(lib_dir)
        with open(os.path.join(lib_dir, "LibClass.smali"), "w") as f:
            f.write(".class public Landroidx/core/LibClass;\n")
            f.write(".method public doSomething()V\n")
            f.write("invoke-virtual {v0}, Landroid/telephony/TelephonyManager;->getDeviceId()Ljava/lang/String;\n")
            f.write(".end method\n")

        # Create a target app file with an exact hit, a subclass hit, and a reflection flag
        app_dir = os.path.join(temp_dir, "com", "example", "app")
        os.makedirs(app_dir)
        with open(os.path.join(app_dir, "MainActivity.smali"), "w") as f:
            f.write(".class public Lcom/example/app/MainActivity;\n")
            
            # Exact hit method
            f.write(".method public exactHit()V\n")
            f.write("invoke-virtual {v0}, Landroid/telephony/TelephonyManager;->getDeviceId()Ljava/lang/String;\n")
            f.write(".end method\n")
            
            # Subclass hit method
            f.write(".method public subclassHit()V\n")
            f.write("invoke-virtual {v0}, Lcom/example/MyManager;->getDeviceId()Ljava/lang/String;\n") # Diff class, same sig
            f.write(".end method\n")
            
            # Reflection method
            f.write(".method public reflectHit()V\n")
            f.write("invoke-virtual {v0}, Ljava/lang/reflect/Method;->invoke(Ljava/lang/Object;[Ljava/lang/Object;)Ljava/lang/Object;\n")
            f.write(".end method\n")
            
            # Native method
            f.write(".method public native doNative()V\n")
            f.write(".end method\n")

        yield temp_dir

def test_scanner(smali_workspace):
    # Mock SuSi sources and sinks
    sources = {
        "Landroid/telephony/TelephonyManager;->getDeviceId()Ljava/lang/String;": {"category": "TELEPHONY", "original_soot_signature": ""}
    }
    sinks = {}
    
    sec_sources = {
        ("getDeviceId", "()Ljava/lang/String;"): {"category": "TELEPHONY", "original_soot_signature": ""}
    }
    sec_sinks = {}
    
    # Configure scanner with default skip_packages (which includes androidx/)
    scanner = Scanner(sources, sinks, sec_sources, sec_sinks)
    
    results = list(scanner.scan_directories([smali_workspace], workers=1))
    
    # Assertions
    # 1. Skipped file shouldn't produce hits
    for r in results:
        assert "androidx" not in r["file"]
        
    hits = [r for r in results if r["type"] == "hit"]
    flags = [r for r in results if r["type"] == "flag"]
    
    # We expect 2 hits (exact + subclass)
    assert len(hits) == 2
    
    exact_hit = next(h for h in hits if h["method"] == "exactHit")
    assert exact_hit["match_type"] == "exact"
    assert exact_hit["target_signature"] == "Landroid/telephony/TelephonyManager;->getDeviceId()Ljava/lang/String;"
    
    subclass_hit = next(h for h in hits if h["method"] == "subclassHit")
    assert subclass_hit["match_type"] == "name_descriptor"
    assert subclass_hit["target_signature"] == "Lcom/example/MyManager;->getDeviceId()Ljava/lang/String;"
    
    # We expect 2 flags (reflection + native_method)
    assert len(flags) == 2
    flag_types = [f["flag"] for f in flags]
    assert "reflection" in flag_types
    assert "native_method" in flag_types
