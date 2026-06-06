from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_rag_query_requires_authentication():
    response = client.post('/api/v1/rag/query', json={
        'ticker': 'NVDA',
        'question': 'What risks does NVIDIA mention regarding competition?'
    })
    assert response.status_code == 401


def test_rag_ingest_requires_authentication():
    response = client.post('/api/v1/rag/ingest/NVDA')
    assert response.status_code == 401
