import pytest
from fallback_analyzer.linker import Linker, Finding
from fallback_analyzer.manifest import ManifestData

class DummyPermissionMapper:
    def get_permissions_for_signature(self, signature):
        if "getDeviceId" in signature:
            return ["android.permission.READ_PHONE_STATE"]
        return []

def test_linker_levels():
    manifest_data = ManifestData(
        package_name="com.example",
        target_sdk=30,
        permissions={"android.permission.READ_PHONE_STATE"},
        components={"Lcom/example/MainActivity;"}
    )
    mapper = DummyPermissionMapper()
    linker = Linker(manifest_data, mapper, enable_l4=True)
    
    # Hits
    src_l1 = {"kind": "source", "class": "Lcom/example/A;", "method": "m1", "target_signature": "Landroid/telephony/TelephonyManager;->getDeviceId()Ljava/lang/String;", "category": "TELEPHONY"}
    snk_l1 = {"kind": "sink", "class": "Lcom/example/A;", "method": "m1"}
    
    src_l2 = {"kind": "source", "class": "Lcom/example/B;", "method": "m1", "target_signature": "Landroid/telephony/TelephonyManager;->getDeviceId()Ljava/lang/String;", "category": "TELEPHONY"}
    snk_l2 = {"kind": "sink", "class": "Lcom/example/B;", "method": "m2"}
    
    src_l3 = {"kind": "source", "class": "Lcom/example/MainActivity$1;", "method": "run", "target_signature": "Landroid/telephony/TelephonyManager;->getDeviceId()Ljava/lang/String;", "category": "TELEPHONY"}
    snk_l3 = {"kind": "sink", "class": "Lcom/example/MainActivity;", "method": "onCreate"}
    
    src_l4 = {"kind": "source", "class": "Lcom/example/C;", "method": "m1", "target_signature": "Landroid/telephony/TelephonyManager;->getDeviceId()Ljava/lang/String;", "category": "TELEPHONY"}
    snk_l4 = {"kind": "sink", "class": "Lcom/example/D;", "method": "m2"}
    
    call_edges = {
        "Lcom/example/C;->m1": ["Lcom/example/D;->m2"]
    }
    
    hits = [src_l1, snk_l1, src_l2, snk_l2, src_l3, snk_l3, src_l4, snk_l4]
    
    findings = linker.link(hits, call_edges)
    
    assert len(findings) == 4
    
    l1_finding = next(f for f in findings if f.source == src_l1)
    assert l1_finding.link_level == "L1"
    assert l1_finding.sink == snk_l1
    assert l1_finding.permission_granted is True
    
    l2_finding = next(f for f in findings if f.source == src_l2)
    assert l2_finding.link_level == "L2"
    assert l2_finding.sink == snk_l2
    
    l3_finding = next(f for f in findings if f.source == src_l3)
    assert l3_finding.link_level == "L3"
    assert l3_finding.sink == snk_l3
    
    l4_finding = next(f for f in findings if f.source == src_l4)
    assert l4_finding.link_level == "L4"
    assert l4_finding.sink == snk_l4
