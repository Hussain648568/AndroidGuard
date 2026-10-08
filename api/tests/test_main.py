import pytest
from fastapi.testclient import TestClient
from api.main import app, analysis_jobs
import json
import os

client = TestClient(app)

def test_upload_apk_endpoint():
    # Create a dummy APK file content
    dummy_apk_content = b"PK\x03\x04Dummy APK Content for testing"
    
    # 1. Test POST /api/v1/analyze
    response = client.post(
        "/api/v1/analyze",
        files={"file": ("test_app.apk", dummy_apk_content, "application/vnd.android.package-archive")}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "run_id" in data
    assert "message" in data
    
    run_id = data["run_id"]
    
    # 2. Test GET /api/v1/status/{run_id}
    status_response = client.get(f"/api/v1/status/{run_id}")
    assert status_response.status_code == 200
    status_data = status_response.json()
    
    # Since background tasks run, it might be 'queued', 'running', or finished depending on event loop
    assert status_data["status"] in ["queued", "running", "success", "failed"]

def test_invalid_file_upload():
    dummy_txt_content = b"Not an APK"
    response = client.post(
        "/api/v1/analyze",
        files={"file": ("test.txt", dummy_txt_content, "text/plain")}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "File must be an APK."

def test_status_not_found():
    response = client.get("/api/v1/status/invalid-uuid-1234")
    assert response.status_code == 404

