"""Testes do CRUD de leads — escritos ANTES da implementação (TDD)."""

# ─── Helpers ──────────────────────────────────────────────────────
VALID_LEAD = {
    "nome": "João Silva",
    "empresa": "Acme Corp",
    "contato": "joao@acme.com",
    "instagram": "@joaosilva",
    "produto": "Portfólio",
    "dificuldade": "Médio",
    "status": "Não contatado",
    "motivo_perda": None,
    "ultimo_contato": None,
    "arquivos": [],
}

VALID_LEAD_2 = {
    "nome": "Maria Souza",
    "empresa": "Beta LLC",
    "contato": "5511999998888",
    "instagram": "@mariasouza",
    "produto": "Sistema",
    "dificuldade": "Fácil",
    "status": "Negociando",
    "motivo_perda": None,
    "ultimo_contato": "2026-01-15T10:30:00",
    "arquivos": [],
}


# ─── CREATE ───────────────────────────────────────────────────────
class TestCreateLead:
    def test_create_lead_success(self, client):
        """POST /api/v1/leads deve criar um lead e retornar 201."""
        res = client.post("/api/v1/leads", json=VALID_LEAD)
        assert res.status_code == 201
        body = res.json()
        assert body["nome"] == "João Silva"
        assert body["id"] is not None

    def test_create_lead_returns_all_fields(self, client):
        """Resposta deve conter todos os campos do schema."""
        res = client.post("/api/v1/leads", json=VALID_LEAD)
        body = res.json()
        for field in VALID_LEAD:
            assert field in body, f"Campo '{field}' ausente na resposta"

    def test_create_lead_missing_required_field(self, client):
        """Campo obrigatório ausente → 422."""
        res = client.post("/api/v1/leads", json={"nome": "Sem resto"})
        assert res.status_code == 422

    def test_create_lead_invalid_status(self, client):
        """Status fora do enum → 422."""
        lead = {**VALID_LEAD, "status": "QualquerCoisa"}
        res = client.post("/api/v1/leads", json=lead)
        assert res.status_code == 422

    def test_create_lead_invalid_dificuldade(self, client):
        """Dificuldade fora do enum → 422."""
        lead = {**VALID_LEAD, "dificuldade": "Impossível"}
        res = client.post("/api/v1/leads", json=lead)
        assert res.status_code == 422

    def test_create_lead_invalid_produto(self, client):
        """Produto fora do enum → 422."""
        lead = {**VALID_LEAD, "produto": "App Mobile"}
        res = client.post("/api/v1/leads", json=lead)
        assert res.status_code == 422

    def test_create_lead_extra_field_rejected(self, client):
        """Campo fora do schema → 422 (Pydantic strict)."""
        lead = {**VALID_LEAD, "hacker": "payload"}
        res = client.post("/api/v1/leads", json=lead)
        assert res.status_code == 422


# ─── FORMATO DE ERRO ──────────────────────────────────────────────
class TestErrorFormat:
    def test_validation_error_is_problem_json(self, client):
        """422 deve seguir RFC 7807 com `detail` STRING.

        O FastAPI devolve `{"detail": [...]}` (lista) por padrão; o
        frontend lia `detail` como texto e exibia "[object Object]".
        """
        res = client.post("/api/v1/leads", json={"nome": ""})
        assert res.status_code == 422
        assert res.headers["content-type"] == "application/problem+json"
        body = res.json()
        assert body["status"] == 422
        assert isinstance(body["detail"], str)
        assert body["detail"].strip()
        assert isinstance(body["errors"], list)
        assert body["errors"][0]["field"]
        assert body["errors"][0]["message"]

    def test_validation_error_message_is_in_portuguese(self, client):
        """Mensagens de validação em PT-BR (Pydantic devolve em inglês)."""
        res = client.post("/api/v1/leads", json={"nome": ""})
        detail = res.json()["detail"]
        assert "campo obrigatório" in detail  # produto/dificuldade ausentes
        assert "nome" in detail

    def test_validation_error_has_request_id(self, client):
        """422 também carrega o request_id para rastreio no log."""
        res = client.post("/api/v1/leads", json={})
        assert res.json()["instance"]
        assert res.headers["x-request-id"]


# ─── READ ─────────────────────────────────────────────────────────
class TestReadLeads:
    def test_list_leads_empty(self, client):
        """GET /api/v1/leads sem dados → lista vazia."""
        res = client.get("/api/v1/leads")
        assert res.status_code == 200
        body = res.json()
        assert isinstance(body, list)

    def test_list_leads_after_create(self, client):
        """Leads criados devem aparecer na listagem."""
        client.post("/api/v1/leads", json=VALID_LEAD)
        client.post("/api/v1/leads", json=VALID_LEAD_2)
        res = client.get("/api/v1/leads")
        body = res.json()
        assert len(body) == 2

    def test_get_lead_by_id(self, client):
        """GET /api/v1/leads/{id} retorna o lead correto."""
        create = client.post("/api/v1/leads", json=VALID_LEAD)
        lead_id = create.json()["id"]
        res = client.get(f"/api/v1/leads/{lead_id}")
        assert res.status_code == 200
        assert res.json()["nome"] == "João Silva"

    def test_get_lead_not_found(self, client):
        """ID inexistente → 404 problem+json."""
        res = client.get("/api/v1/leads/99999")
        assert res.status_code == 404
        assert res.headers["content-type"] == "application/problem+json"


# ─── UPDATE ───────────────────────────────────────────────────────
class TestUpdateLead:
    def test_update_lead_success(self, client):
        """PUT /api/v1/leads/{id} atualiza o lead."""
        create = client.post("/api/v1/leads", json=VALID_LEAD)
        lead_id = create.json()["id"]
        update = {**VALID_LEAD, "status": "Fechado", "nome": "João Atualizado"}
        res = client.put(f"/api/v1/leads/{lead_id}", json=update)
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "Fechado"
        assert body["nome"] == "João Atualizado"

    def test_update_lead_partial(self, client):
        """PATCH /api/v1/leads/{id} atualiza apenas campos informados."""
        create = client.post("/api/v1/leads", json=VALID_LEAD)
        lead_id = create.json()["id"]
        res = client.patch(
            f"/api/v1/leads/{lead_id}", json={"status": "Negociando"}
        )
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "Negociando"
        assert body["nome"] == "João Silva"  # não alterado

    def test_update_lead_not_found(self, client):
        """Atualizar ID inexistente → 404."""
        res = client.put("/api/v1/leads/99999", json=VALID_LEAD)
        assert res.status_code == 404

    def test_update_lead_invalid_status(self, client):
        """Status inválido no update → 422."""
        create = client.post("/api/v1/leads", json=VALID_LEAD)
        lead_id = create.json()["id"]
        update = {**VALID_LEAD, "status": "Invalido"}
        res = client.put(f"/api/v1/leads/{lead_id}", json=update)
        assert res.status_code == 422


# ─── DELETE ───────────────────────────────────────────────────────
class TestDeleteLead:
    def test_delete_lead_success(self, client):
        """DELETE /api/v1/leads/{id} remove o lead."""
        create = client.post("/api/v1/leads", json=VALID_LEAD)
        lead_id = create.json()["id"]
        res = client.delete(f"/api/v1/leads/{lead_id}")
        assert res.status_code == 204

    def test_delete_lead_gone_after(self, client):
        """Após deletar, GET deve retornar 404."""
        create = client.post("/api/v1/leads", json=VALID_LEAD)
        lead_id = create.json()["id"]
        client.delete(f"/api/v1/leads/{lead_id}")
        res = client.get(f"/api/v1/leads/{lead_id}")
        assert res.status_code == 404

    def test_delete_lead_not_found(self, client):
        """Deletar ID inexistente → 404."""
        res = client.delete("/api/v1/leads/99999")
        assert res.status_code == 404


# ─── EXPORT CSV ───────────────────────────────────────────────────
class TestExportCSV:
    def test_export_csv_success(self, client):
        """GET /api/v1/leads/export deve retornar text/csv."""
        client.post("/api/v1/leads", json=VALID_LEAD)
        res = client.get("/api/v1/leads/export")
        assert res.status_code == 200
        assert "text/csv" in res.headers["content-type"]

    def test_export_csv_has_headers(self, client):
        """CSV deve conter cabeçalhos corretos."""
        client.post("/api/v1/leads", json=VALID_LEAD)
        res = client.get("/api/v1/leads/export")
        lines = res.text.strip().split("\n")
        headers = lines[0]
        for col in [
            "Nome",
            "Empresa",
            "Contato",
            "Instagram",
            "Produto",
            "Dificuldade",
            "Status",
            "Motivo da perda",
            "Último contato",
            "Arquivos",
        ]:
            assert col in headers, f"Coluna '{col}' ausente no CSV"

    def test_export_csv_contains_data(self, client):
        """CSV deve conter os dados do lead."""
        client.post("/api/v1/leads", json=VALID_LEAD)
        res = client.get("/api/v1/leads/export")
        assert "João Silva" in res.text
        assert "Acme Corp" in res.text

    def test_export_csv_empty(self, client):
        """CSV vazio deve ter apenas cabeçalhos."""
        res = client.get("/api/v1/leads/export")
        assert res.status_code == 200
        lines = res.text.strip().split("\n")
        assert len(lines) == 1  # só cabeçalho
