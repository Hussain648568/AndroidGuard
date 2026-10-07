import pytest
from fallback_analyzer.analyzer import Analyzer
from fallback_analyzer.models import SuSiTarget, FindingLocation

def test_link_findings():
    analyzer = Analyzer("dummy.apk", "dummy_src.txt", "dummy_snk.txt")
    
    src = SuSiTarget("src_sig", "CAT", "perm.A")
    snk = SuSiTarget("snk_sig", "LOG")
    
    # Found in same method
    loc1 = FindingLocation("file1.smali", "Lcom/A;", "method1", 10)
    loc2 = FindingLocation("file1.smali", "Lcom/A;", "method1", 20)
    
    findings = analyzer._link_findings(
        [(src, loc1)],
        [(snk, loc2)],
        permissions={"perm.A"}
    )
    
    assert len(findings) == 1
    assert findings[0].score == 100
    assert "same_method" in findings[0].flags
    assert "permission_corroborated" in findings[0].flags

def test_link_findings_missing_permission():
    analyzer = Analyzer("dummy.apk", "dummy_src.txt", "dummy_snk.txt")
    
    src = SuSiTarget("src_sig", "CAT", "perm.A")
    snk = SuSiTarget("snk_sig", "LOG")
    
    loc1 = FindingLocation("file1.smali", "Lcom/A;", "method1", 10)
    loc2 = FindingLocation("file1.smali", "Lcom/A;", "method1", 20)
    
    findings = analyzer._link_findings(
        [(src, loc1)],
        [(snk, loc2)],
        permissions={"perm.B"} # Wrong permission
    )
    
    # Should be filtered out
    assert len(findings) == 0

def test_link_findings_same_class():
    analyzer = Analyzer("dummy.apk", "dummy_src.txt", "dummy_snk.txt")
    
    src = SuSiTarget("src_sig", "CAT") # no perm required
    snk = SuSiTarget("snk_sig", "LOG")
    
    loc1 = FindingLocation("file1.smali", "Lcom/A;", "method1", 10)
    loc2 = FindingLocation("file1.smali", "Lcom/A;", "method2", 20)
    
    findings = analyzer._link_findings(
        [(src, loc1)],
        [(snk, loc2)],
        permissions=set()
    )
    
    assert len(findings) == 1
    assert findings[0].score == 50
    assert "same_class" in findings[0].flags
