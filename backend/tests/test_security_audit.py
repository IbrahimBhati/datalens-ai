"""
Security & Privacy Audit Test Suite for DataLens AI.

Verifies:
1. Path traversal resistance across endpoints and analyzers
2. Filename sanitization against malicious filenames
3. Temporary dataset lifecycle & explicit user deletion
4. Automatic expired dataset pruning (TTL)
5. In-memory sliding-window rate limiting
6. Safe error handling (no stack trace exposure)
7. Safe MIME and malformed file rejection
"""

import io
import os
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.config import UPLOAD_DIR
from app.main import app, _rate_limit_records
from app.services.dataset_service import cleanup_expired_datasets, delete_dataset, sanitize_filename


@pytest.fixture
def client():
    # Clear rate limit records before each test
    _rate_limit_records.clear()
    return TestClient(app)


def test_filename_sanitization():
    """Verify malicious filenames are safely neutralized."""
    # Path traversal patterns
    assert ".." not in sanitize_filename("../../../etc/passwd.csv")
    assert "\\" not in sanitize_filename("..\\..\\windows\\system32\\cmd.exe.csv")
    
    # Script tags and characters
    clean = sanitize_filename("<script>alert('xss')</script>.json")
    assert "<" not in clean and ">" not in clean and "'" not in clean
    
    # Null bytes
    null_name = sanitize_filename("safe_file\x00_hidden.csv")
    assert "\x00" not in null_name
    
    # Edge cases
    assert sanitize_filename("...") == "dataset"
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        sanitize_filename("")


def test_path_traversal_prevention_on_endpoints(client):
    """Endpoints must reject malformed, traversed, or invalid dataset IDs with 400 Bad Request."""
    traversal_ids = [
        "../secrets",
        "..\\..\\windows",
        "../../uploads/test",
        "short",  # < 8 chars
        "invalid*char$id!",
        "a" * 100,  # > 64 chars
        "/etc/passwd",
    ]
    
    for bad_id in traversal_ids:
        # Profile endpoint
        resp = client.post(f"/api/datasets/{bad_id}/profile")
        assert resp.status_code in (400, 404), f"Expected 400 or 404 for bad id {bad_id}, got {resp.status_code}"
        
        # Analyze endpoint
        resp = client.post(f"/api/datasets/{bad_id}/analyze")
        assert resp.status_code in (400, 404)
        
        # Score endpoint
        resp = client.post(f"/api/datasets/{bad_id}/score")
        assert resp.status_code in (400, 404)
        
        # Delete endpoint
        resp = client.delete(f"/api/datasets/{bad_id}")
        assert resp.status_code in (400, 404)


def test_user_initiated_dataset_deletion(client):
    """User can explicitly delete uploaded dataset and its cleaned variant."""
    # Upload test CSV
    csv_data = b"col_a,col_b\n1,hello\n2,world\n"
    upload_resp = client.post(
        "/api/datasets/upload",
        files={"file": ("temp_for_delete.csv", io.BytesIO(csv_data), "text/csv")},
    )
    assert upload_resp.status_code == 200
    dataset_id = upload_resp.json()["dataset_id"]
    
    # Verify file exists on disk
    upload_dir = Path(UPLOAD_DIR).resolve()
    orig_file = upload_dir / f"{dataset_id}.csv"
    assert orig_file.exists()
    
    # Call clean to create a cleaned file
    clean_resp = client.post(f"/api/datasets/{dataset_id}/clean")
    assert clean_resp.status_code == 200
    cleaned_file = upload_dir / f"{dataset_id}_cleaned.csv"
    assert cleaned_file.exists()
    
    # Explicit delete
    del_resp = client.delete(f"/api/datasets/{dataset_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "success"
    
    # Verify both files are permanently removed from storage
    assert not orig_file.exists()
    assert not cleaned_file.exists()
    
    # Second delete returns 404
    del_resp2 = client.delete(f"/api/datasets/{dataset_id}")
    assert del_resp2.status_code == 404


def test_cleanup_expired_datasets():
    """Verify expired dataset files are pruned based on TTL."""
    upload_dir = Path(UPLOAD_DIR).resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a dummy old file
    old_file = upload_dir / "old_dataset_test_audit_001.csv"
    old_file.write_text("a,b\n1,2\n", encoding="utf-8")
    
    # Artificially set mtime to 48 hours ago
    past_time = time.time() - (48 * 3600)
    os.utime(old_file, (past_time, past_time))
    
    # Create a fresh file
    fresh_file = upload_dir / "fresh_dataset_test_audit_002.csv"
    fresh_file.write_text("a,b\n3,4\n", encoding="utf-8")
    
    # Prune datasets older than 24 hours
    pruned = cleanup_expired_datasets(max_age_hours=24.0)
    assert pruned >= 1
    assert not old_file.exists()
    assert fresh_file.exists()
    
    # Clean up fresh file
    if fresh_file.exists():
        fresh_file.unlink()


def test_rate_limiting_enforcement(client, monkeypatch):
    """Verify exceeding rate limit returns 429 Too Many Requests."""
    from app import main
    # Lower limit temporarily for rapid test
    monkeypatch.setattr(main, "RATE_LIMIT_REQUESTS_PER_MINUTE", 5)
    
    for i in range(5):
        resp = client.get("/api/health")
        assert resp.status_code == 200
    
    # 5 requests to non-exempt endpoint
    for i in range(5):
        resp = client.post("/api/datasets/11111111-2222-3333-4444-555555555555/profile")
        assert resp.status_code in (400, 404)
        
    # 6th request triggers rate limit
    blocked_resp = client.post("/api/datasets/11111111-2222-3333-4444-555555555555/profile")
    assert blocked_resp.status_code == 429
    assert "Too many requests" in blocked_resp.json()["detail"]
    assert blocked_resp.headers.get("Retry-After") == "60"


def test_unhandled_error_does_not_leak_stacktrace(client, monkeypatch):
    """Unhandled server exceptions return generic message without stack trace."""
    def faulty_upload(*args, **kwargs):
        raise RuntimeError("SecretDatabaseConnectionStringPassword123 failed!")

    monkeypatch.setattr("app.api.datasets.handle_dataset_upload", faulty_upload)
    
    # Also tell test client not to re-raise server exceptions
    test_client = TestClient(app, raise_server_exceptions=False)
    resp = test_client.post(
        "/api/datasets/upload",
        files={"file": ("test.csv", io.BytesIO(b"a,b\n1,2"), "text/csv")},
    )
    assert resp.status_code == 500
    # Must NOT contain the internal exception message or trace
    assert "SecretDatabaseConnectionStringPassword123" not in resp.text
    assert "Traceback" not in resp.text
    assert resp.json()["detail"] == "An internal server error occurred. Please try again later."


def test_disallowed_mime_types(client):
    """Disallowed executable or script MIME types must be rejected."""
    bad_mimes = [
        "application/x-msdownload",
        "application/javascript",
        "text/html",
        "image/png",
    ]
    for mime in bad_mimes:
        resp = client.post(
            "/api/datasets/upload",
            files={"file": ("test.csv", io.BytesIO(b"a,b\n1,2"), mime)},
        )
        assert resp.status_code == 400
        assert "Disallowed MIME type" in resp.json()["detail"] or "not valid" in resp.json()["detail"]
