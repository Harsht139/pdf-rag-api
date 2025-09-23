import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    return TestClient(app)


class DummyTable:
    def __init__(self, store):
        self.store = store

    def insert(self, payload):
        self.store.append(("insert", payload))
        return self

    def execute(self):
        return SimpleNamespace(data=None)


class DummySupabase:
    def __init__(self, store):
        self.store = store

    def table(self, name):
        self.store.append(("table", name))
        return DummyTable(self.store)


@pytest.fixture()
def monkey_clients(monkeypatch):
    calls = []

    def fake_upload_bytes_to_supabase_storage(
        *, file_bytes, object_path, content_type="application/pdf"
    ):
        calls.append(("upload", object_path, len(file_bytes), content_type))
        return {
            "path": f"pdfs/{object_path}",
            "public_url": f"https://supabase.local/{object_path}",
        }

    def fake_get_supabase_client():
        return DummySupabase(calls)

    async def fake_fetch_bytes_from_url(url: str):
        # Return small PDF-like bytes
        return b"%PDF-1.4\n...", "application/pdf"

    # Patch symbols as imported into the endpoint module
    monkeypatch.setattr(
        "app.api.v1.endpoints.documents.upload_bytes_to_supabase_storage",
        fake_upload_bytes_to_supabase_storage,
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.documents.get_supabase_client", fake_get_supabase_client
    )
    monkeypatch.setattr(
        "app.api.v1.endpoints.documents.fetch_bytes_from_url", fake_fetch_bytes_from_url
    )

    # Avoid HTTP HEAD in _resolve_download_url
    async def fake_resolve(url: str) -> str:
        return url

    monkeypatch.setattr(
        "app.api.v1.endpoints.documents._resolve_download_url", fake_resolve
    )
    return calls


def test_upload_file_success(client, monkey_clients):
    files = {"file": ("sample.pdf", b"%PDF-1.4\n...")}
    resp = client.post("/api/v1/upload", files=files)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] in {"processing", "pending_storage", "ready"}
    assert data["public_url"].startswith("https://supabase.local/")


def test_upload_link_direct_pdf_success(client, monkey_clients):
    payload = {"pdf_url": "https://example.com/file.pdf"}
    resp = client.post("/api/v1/upload_link", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] in {"processing", "pending_storage", "ready"}


def test_upload_link_unsupported(client, monkeypatch):
    # Force HEAD to fail content-type check by pointing to non-pdf link and making HEAD 404
    # no direct import needed; we patch httpx client below

    async def fake_head_fail(url):
        class R:
            status_code = 404
            headers = {}

        return R()

    class DummyAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def head(self, url):
            return await fake_head_fail(url)

    monkeypatch.setattr(
        "app.api.v1.endpoints.documents.httpx.AsyncClient", DummyAsyncClient
    )

    resp = client.post(
        "/api/v1/upload_link",
        json={"pdf_url": "https://sharepoint.example.com/view?id=1"},
    )
    assert resp.status_code == 400
    assert "Unsupported link type" in resp.text
