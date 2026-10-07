import pytest
from fallback_analyzer.scorer import Scorer
from fallback_analyzer.linker import Finding

def test_high_confidence():
    scorer = Scorer()
    
    # L1, perm granted, exact match
    f1 = Finding(
        source={"match_type": "exact"},
        sink={"match_type": "exact"},
        link_level="L1",
        permission_required=["android.permission.READ_PHONE_STATE"],
        permission_granted=True,
        flags=[]
    )
    
    results = scorer.score([f1])
    assert results[0]["confidence"] == "HIGH"
    assert results[0]["analysis_tier"] == "heuristic"
    assert "likely_library_or_dead_code" not in results[0]["flags"]

def test_medium_confidence_l3():
    scorer = Scorer()
    f = Finding(
        source={"match_type": "exact"},
        sink={"match_type": "exact"},
        link_level="L3",
        permission_required=["android.permission.READ_PHONE_STATE"],
        permission_granted=True,
        flags=[]
    )
    results = scorer.score([f])
    assert results[0]["confidence"] == "MEDIUM"

def test_medium_confidence_name_descriptor():
    scorer = Scorer()
    # L1 but name_descriptor match
    f = Finding(
        source={"match_type": "name_descriptor"},
        sink={"match_type": "exact"},
        link_level="L1",
        permission_required=["android.permission.READ_PHONE_STATE"],
        permission_granted=True,
        flags=[]
    )
    results = scorer.score([f])
    assert results[0]["confidence"] == "MEDIUM"

def test_low_confidence_unlinked():
    scorer = Scorer()
    f = Finding(
        source={"match_type": "exact"},
        sink=None,
        link_level="UNLINKED",
        permission_required=["android.permission.READ_PHONE_STATE"],
        permission_granted=True,
        flags=[]
    )
    results = scorer.score([f])
    assert results[0]["confidence"] == "LOW"

def test_downgrade_missing_permission():
    scorer = Scorer()
    # L1 exact match, but permission not granted
    f = Finding(
        source={"match_type": "exact"},
        sink={"match_type": "exact"},
        link_level="L1",
        permission_required=["android.permission.READ_PHONE_STATE"],
        permission_granted=False,
        flags=[]
    )
    results = scorer.score([f])
    assert results[0]["confidence"] == "LOW"
    assert "likely_library_or_dead_code" in results[0]["flags"]
