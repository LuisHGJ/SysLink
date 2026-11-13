"""Testes do health check."""


def test_health_check(client):
    """GET /health deve retornar 200 com status ok."""
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "environment" in body


def test_health_check_has_request_id(client):
    """Toda resposta deve incluir x-request-id."""
    response = client.get("/health")
    assert "x-request-id" in response.headers


def test_unknown_route_returns_problem_json(client):
    """Rota inexistente deve retornar application/problem+json."""
    response = client.get("/nonexistent")
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["status"] == 404
    assert "detail" in body
    assert "stack" not in body  # nunca expor stack trace
