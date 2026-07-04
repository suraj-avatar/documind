"""
test_api.py — Integration tests for the DocuMind FastAPI backend.

These tests use FastAPI's TestClient and do NOT require a live server.
Tests that call /ask or /debug/retrieval are skipped if the vectorstore
is empty (fresh environment with no ingested documents).
"""

import io
import pytest


# ── /health ─────────────────────────────────────────────────

class TestHealth:
    def test_health_returns_200(self, client):
        """Health endpoint must return HTTP 200."""
        res = client.get('/health')
        assert res.status_code == 200

    def test_health_has_status_ok(self, client):
        """Response body must contain status=ok."""
        data = client.get('/health').json()
        assert data['status'] == 'ok'

    def test_health_has_expected_keys(self, client):
        """Response must include all expected metadata fields."""
        data = client.get('/health').json()
        assert 'vectorstore_chunks' in data
        assert 'embedding_model' in data
        assert 'llm_model' in data

    def test_health_embedding_model(self, client):
        """Embedding model reported must match project config."""
        data = client.get('/health').json()
        assert 'bge-base-en-v1.5' in data['embedding_model']


# ── / root ───────────────────────────────────────────────────

class TestRoot:
    def test_root_returns_200(self, client):
        res = client.get('/')
        assert res.status_code == 200

    def test_root_message(self, client):
        data = client.get('/').json()
        assert 'message' in data
        assert 'running' in data['message'].lower()


# ── /ask ─────────────────────────────────────────────────────

class TestAsk:
    def test_ask_empty_question_rejected(self, client):
        """A completely empty question body should return 422."""
        res = client.post('/ask', json={})
        assert res.status_code == 422

    def test_ask_returns_answer_and_sources(self, client):
        """
        Skipped when vectorstore is empty (CI / fresh environment).
        On a populated vectorstore, response must contain answer + sources.
        """
        health = client.get('/health').json()
        if health.get('vectorstore_chunks', 0) == 0:
            pytest.skip('Vectorstore is empty — run ingest.py first')

        res = client.post('/ask', json={
            'question': 'What is the main topic of the uploaded documents?',
            'session_id': 'pytest-session',
        })
        assert res.status_code == 200
        data = res.json()
        assert 'answer' in data
        assert isinstance(data['answer'], str)
        assert len(data['answer']) > 0
        assert 'sources' in data
        assert isinstance(data['sources'], list)

    def test_ask_uses_session_id(self, client):
        """Different session IDs should be accepted without error."""
        health = client.get('/health').json()
        if health.get('vectorstore_chunks', 0) == 0:
            pytest.skip('Vectorstore is empty — run ingest.py first')

        for sid in ['session-a', 'session-b']:
            res = client.post('/ask', json={
                'question': 'Hello',
                'session_id': sid,
            })
            assert res.status_code == 200


# ── /upload ──────────────────────────────────────────────────

class TestUpload:
    def test_upload_non_pdf_rejected(self, client):
        """Uploading a non-PDF file must return HTTP 415."""
        fake_txt = io.BytesIO(b'this is plain text, not a pdf')
        res = client.post(
            '/upload',
            files=[('files', ('test.txt', fake_txt, 'text/plain'))],
        )
        assert res.status_code == 415

    def test_upload_empty_request_rejected(self, client):
        """Uploading with no files must return HTTP 422."""
        res = client.post('/upload')
        assert res.status_code == 422

    def test_upload_invalid_pdf_returns_error(self, client):
        """
        A file with a .pdf extension but invalid content should either
        succeed with 0 chunks or return a 500 — not crash silently.
        """
        bad_pdf = io.BytesIO(b'%PDF fake content not a real pdf')
        res = client.post(
            '/upload',
            files=[('files', ('broken.pdf', bad_pdf, 'application/pdf'))],
        )
        # Either ingested 0 chunks successfully or raised a 500
        assert res.status_code in (200, 500)


# ── /debug/retrieval ─────────────────────────────────────────

class TestDebugRetrieval:
    def test_debug_requires_query_param(self, client):
        """Missing ?q= query parameter must return 422."""
        res = client.get('/debug/retrieval')
        assert res.status_code == 422

    def test_debug_returns_structured_response(self, client):
        """Response must include query and chunks list."""
        health = client.get('/health').json()
        if health.get('vectorstore_chunks', 0) == 0:
            pytest.skip('Vectorstore is empty — run ingest.py first')

        res = client.get('/debug/retrieval', params={'q': 'test query'})
        assert res.status_code == 200
        data = res.json()
        assert 'query' in data
        assert 'chunks' in data
        assert isinstance(data['chunks'], list)
