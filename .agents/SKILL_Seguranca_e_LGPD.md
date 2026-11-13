# Skills Roadmap — Engenharia de Software & Segurança
**Portal InovaSkill | Luis | 2026**

---

## 1. Segredos & Configuração de Ambiente
**Skill ID:** `env-secrets-management`  
**Status:** Proposta | **Prioridade:** 🔴 Alta  
**Tags:** segurança, configuração, deployment, ci-cd

### Propósito
Garantir que chaves de API, credenciais de banco, tokens e demais secrets nunca sejam commitados em repo público ou vazem em logs de erro — usando gerenciadores de secrets (AWS Secrets Manager/Parameter Store) em produção.

### Triggers
- Código que inicializa conexão de banco, auth externa, ou varia por ambiente
- Review de `.env`, `.env.local`, ou configuração em arquivo
- Setup de projeto novo que precisa de credenciais (DB, APIs)
- Deploy/CI que precisa acessar secrets
- Auditoria de logs que pode expor credenciais

### Regras Principais

#### ✅ Fazer
- `.env.example` com placeholders (`DB_PASSWORD=your-password-here`)
- Secrets importados de variáveis de ambiente ou gerenciador (não de arquivo)
- AWS Secrets Manager ou Parameter Store em produção
- Rotação periódica de secrets (política definida)
- Auditoria de acesso a secrets (quem acessou, quando)
- `.env` e `*.key` no `.gitignore` (nunca commitado)
- Secrets nunca logados em plain text

#### ❌ Nunca
- Hardcoded de senha/token no código (`password = "abc123"`)
- Commit de `.env` real, `credentials.json`, `.pem`
- Secrets em comment de código ("TODO: usar senha real")
- Print/log de credencial em error message para cliente
- String de conexão com password em URL de log

### Implementação

#### Checklist de Projeto
- [ ] `.env.example` criado com todas as variáveis necessárias
- [ ] `.env*` e `*.key` adicionados ao `.gitignore`
- [ ] Código usa `os.getenv()` ou `dotenv.load()` (não hardcoded)
- [ ] AWS Secrets Manager/Parameter Store configurado para produção
- [ ] CI tem acesso via IAM role (nunca com chave estática)
- [ ] Logging nunca inclui valores de secrets
- [ ] Documentação de como setup local (sem expor secretos)
- [ ] Alert/audit quando secret é acessado

#### Exemplo FastAPI + Pydantic
```python
# ❌ ERRADO
DB_PASSWORD = "minha_senha_real"  # Nunca!

# ✅ CERTO
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    db_password: str  # Vem de variável de ambiente
    api_key: str
    
    class Config:
        env_file = ".env"  # Só em desenvolvimento
        extra = "forbid"

settings = Settings()
# Em produção: vem de AWS Secrets Manager
```

#### Exemplo `.env.example`
```bash
# Banco de dados
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your-secure-password-here
DB_NAME=portal_inova

# APIs externas
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret

# AWS (rodará com IAM role em produção)
AWS_REGION=us-east-1
AWS_SECRETS_MANAGER_ARN=arn:aws:secretsmanager:...
```

### Matriz de Aplicação

| Contexto | Ação |
|----------|------|
| Dev local | dotenv (.env) + .gitignore |
| Teste (CI) | Secrets do GitHub Actions / GitLab CI |
| Staging | AWS Secrets Manager |
| Produção | AWS Secrets Manager + rotação |

---

## 2. Segurança de Dependências (Supply Chain)
**Skill ID:** `dependency-security`  
**Status:** Proposta | **Prioridade:** 🔴 Alta  
**Tags:** segurança, ci-cd, dependências, vulnerabilidades

### Propósito
Monitorar e atualizar dependências automaticamente, detectar vulnerabilidades no supply chain antes que chegue em produção — evitando patches quebrados, zero-days não corrigidos e "funciona na minha máquina" por versão flutuante.

### Triggers
- Setup de projeto novo com `package.json` / `requirements.txt`
- Review de mudança em dependências
- Merge de dependência desatualizada sem teste
- Build falhando silenciosamente por versão flutuante
- Auditoria de segurança / compliance

### Regras Principais

#### ✅ Fazer
- Dependabot ou Renovate ativo, PR automático de atualização
- `npm audit` / `pip-audit` rodam no CI, build falha em **crítico**
- Lockfile (`package-lock.json`, `poetry.lock`, `pip.freeze`) **sempre** commitado
- Revisão automática de: compatibilidade, breaking changes, segurança
- Changelog/SECURITY.md lido antes de aprovar dependência maior
- `npm ls` / `pip show` para checar versões transitivas
- Política: patch automático, minor com revisão, major com testes

#### ❌ Nunca
- Deletar/atualizar lockfile sem motivo documentado
- Ignorar alerta de `npm audit` ou `pip-audit`
- Usar `*` ou `^` sem upper bound em versão (`"^2.0.0"` vs `"^2.5.0"`)
- Confiar em "última versão" sem testar — sempre teste update
- Dependência não-oficial ou fork sem SR/documentação
- Subir patch de segurança sem rodar testes

### Implementação

#### Checklist de Projeto
- [ ] Dependabot ou Renovate ativado no repo
- [ ] CI roda `npm audit --audit-level=moderate` (ou pip-audit)
- [ ] Build falha em vulnerabilidade **crítica**
- [ ] `package-lock.json` / `poetry.lock` commitado (.gitignore negativo se necessário)
- [ ] GitHub/GitLab Issues: Labels `dependencies`, `security` usadas em auto-PR
- [ ] Policy: "Approval automático para patches, manual para minor/major"
- [ ] Documentação de como fazer update seguro localmente

#### Exemplo GitHub Actions
```yaml
name: Security Audit
on: [push, pull_request]
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: npm ci  # Respeita lockfile exato
      - run: npm audit --audit-level=moderate
        # Falha se critical ou high
```

#### Exemplo Renovate Config
```json
{
  "extends": ["config:base"],
  "schedule": ["before 3am on Monday"],
  "vulnerabilityAlerts": {
    "enabled": true,
    "assignees": ["@luis"]
  },
  "packageRules": [
    {
      "matchUpdateTypes": ["patch"],
      "automerge": true
    },
    {
      "matchUpdateTypes": ["minor"],
      "automerge": false,
      "labels": ["dependencies"]
    }
  ]
}
```

### Matriz de Aplicação

| Tipo | Automatizado | Revisão | Teste |
|------|--------------|---------|-------|
| Patch (segurança) | ✅ Sim | Rápida | Obrigatório |
| Patch (bug) | ✅ Sim | Rápida | Obrigatório |
| Minor | ❌ PR manual | Média | Obrigatório |
| Major | ❌ PR manual | Completa | Obrigatório + staging |

---

## 3. Arquitetura em Camadas — FastAPI
**Skill ID:** `fastapi-layered-architecture`  
**Status:** Proposta | **Prioridade:** 🟠 Média  
**Tags:** arquitetura, fastapi, tdd, qualidade, python

### Propósito
Formalizar separação clara de responsabilidades em FastAPI: `router` → `service` → `repository`. Evita SQL solto em endpoints, facilita TDD (testa lógica sem banco), e mantém código testável e previsível.

### Triggers
- Criação de endpoint novo em FastAPI
- Review de código que mistura lógica de negócio em rota
- Setup de projeto FastAPI novo
- Refatoração para melhorar testabilidade
- Discussão de "onde coloco essa validação?"

### Regras Principais

#### Camada: Router
```python
# fastapi_app/routes/users.py
from fastapi import APIRouter, Depends
from services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", status_code=201)
async def create_user(user_data: UserCreateSchema, 
                      service: UserService = Depends()):
    # ✅ SÓ: receber input, chamar service, retornar schema
    # ❌ NUNCA: SQL, regex complexa, lógica de negócio
    result = service.create_user(user_data)
    return UserResponseSchema.from_orm(result)

@router.get("/{user_id}")
async def get_user(user_id: int, 
                   service: UserService = Depends()):
    user = service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(404, "Not found")
    return UserResponseSchema.from_orm(user)
```

**Responsabilidades:**
- Validação de input (Pydantic schema)
- Chamada ao service
- Tratamento de erro (raise HTTPException)
- Serialização de resposta (schema)

#### Camada: Service
```python
# fastapi_app/services/user_service.py
from repositories.user_repository import UserRepository
from schemas.user_schema import UserCreateSchema
from exceptions import BusinessLogicError

class UserService:
    def __init__(self, repo: UserRepository = Depends()):
        self.repo = repo
    
    def create_user(self, user_data: UserCreateSchema) -> User:
        # ✅ Lógica de negócio: validações, regras
        if self.repo.email_exists(user_data.email):
            raise BusinessLogicError("Email já registrado")
        
        # Segurança: hash de senha
        hashed_pwd = hash_password(user_data.password)
        user_data.password = hashed_pwd
        
        # Delegá ao repository
        return self.repo.create(user_data)
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        # Regras de negócio
        user = self.repo.get_by_id(user_id)
        if user and user.deleted_at:  # Soft delete?
            return None  # Para camada de apresentação, não existe
        return user
```

**Responsabilidades:**
- Validações de negócio
- Transformações de dados
- Orquestração entre repositórios
- ❌ Nunca: SQL direto, HTTP request, envio de email (→ use async tasks)

#### Camada: Repository
```python
# fastapi_app/repositories/user_repository.py
from sqlalchemy.orm import Session
from models.user_model import User

class UserRepository:
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db
    
    def create(self, user_data: UserCreateSchema) -> User:
        # ✅ SÓ: SQL, acesso a BD
        db_user = User(**user_data.dict())
        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)
        return db_user
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()
    
    def email_exists(self, email: str) -> bool:
        return self.db.query(User).filter(
            User.email == email
        ).first() is not None
```

**Responsabilidades:**
- Acesso a dados (SQL via SQLAlchemy)
- Queries complexas
- ❌ Nunca: lógica de negócio, HTTP, validações

### Padrão de Teste

```python
# tests/services/test_user_service.py
def test_create_user_success(mocker):
    """Service: validação + transformação, sem banco"""
    # Arrange
    repo_mock = MagicMock(spec=UserRepository)
    repo_mock.email_exists.return_value = False
    repo_mock.create.return_value = User(id=1, email="test@ex.com")
    
    service = UserService(repo=repo_mock)
    
    # Act
    result = service.create_user(UserCreateSchema(
        email="test@ex.com",
        password="123456"
    ))
    
    # Assert
    assert result.email == "test@ex.com"
    repo_mock.email_exists.assert_called_once()
    repo_mock.create.assert_called_once()

def test_create_user_email_duplicate(mocker):
    """Service: regra de negócio — email duplicado"""
    repo_mock = MagicMock(spec=UserRepository)
    repo_mock.email_exists.return_value = True  # Email já existe
    
    service = UserService(repo=repo_mock)
    
    with pytest.raises(BusinessLogicError):
        service.create_user(UserCreateSchema(email="dup@ex.com", password="123"))
```

### Estrutura de Diretórios
```
fastapi_app/
├── main.py                 # Inicialização FastAPI
├── routes/                 # Routers
│   ├── users.py
│   ├── projects.py
│   └── __init__.py
├── services/               # Services (regra de negócio)
│   ├── user_service.py
│   ├── project_service.py
│   └── __init__.py
├── repositories/           # Repositories (acesso a dado)
│   ├── user_repository.py
│   ├── project_repository.py
│   └── __init__.py
├── models/                 # SQLAlchemy models
│   ├── user_model.py
│   └── __init__.py
├── schemas/                # Pydantic schemas
│   ├── user_schema.py
│   └── __init__.py
├── exceptions/             # Custom exceptions
│   └── __init__.py
├── dependencies.py         # Dependency injection
└── config.py               # Configurações
```

### Checklist de Projeto
- [ ] Routes **não** contêm lógica de negócio (só validação básica)
- [ ] Services orquestram lógica de negócio, usam repositories
- [ ] Repositories encapsulam SQL, não sabem de HTTP/validação
- [ ] Cada serviço tem mock-friendly `__init__(self, repo=Depends())`
- [ ] Testes de service **não** precisam de banco de dados
- [ ] Testes de repository podem usar banco em-memória ou fixture
- [ ] Testes de route verificam HTTP, não lógica (mock service)

---

## 4. Contrato de API Sincronizado (OpenAPI First)
**Skill ID:** `api-contract-sync`  
**Status:** Proposta | **Prioridade:** 🟠 Média  
**Tags:** api, openapi, contrato, frontend, typescript

### Propósito
Manter schema OpenAPI como fonte única de verdade. Frontend gera tipos TypeScript automaticamente — nunca manualmente — e detectar de-sincronização em CI.

### Triggers
- Criação de endpoint novo em FastAPI
- Mudança em request/response schema
- Setup de projeto novo com frontend+backend
- Pull request que toca em contrato de API
- "Erro: campo renomeado no backend, frontend ainda usa nome antigo"

### Regras Principais

#### ✅ Fazer
- FastAPI gera OpenAPI automaticamente (`GET /openapi.json`)
- Frontend usa `openapi-typescript` (gera types TypeScript do schema)
- Types TypeScript **sempre** gerados, nunca escritos à mão
- CI valida: schema é válido + nenhuma breaking change sem major
- Commit de types gerados ao repo (facilita diff)
- Documentação OpenAPI atualizada automaticamente (docstrings FastAPI)
- Versionamento de API: `/v1/users`, `/v2/users`

#### ❌ Nunca
- Types TypeScript escritos à mão (`interface User { ... }`)
- Schema OpenAPI desatualizado vs. código FastAPI real
- Breaking change sem incrementar versão de API
- Frontend "espera" um campo que backend removeu
- Documentação de API em Notion enquanto código muda

### Implementação

#### FastAPI + Auto-OpenAPI
```python
# fastapi_app/main.py
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

app = FastAPI(
    title="Portal InovaSkill API",
    version="1.0.0",
    description="API para gestão de inovação",
)

# FastAPI gera OpenAPI de forma automática

@app.get("/v1/users/{user_id}")
async def get_user(user_id: int):
    """
    Retorna um usuário pelo ID.
    
    - **user_id**: ID único do usuário
    - **Returns**: UserResponse com email, nome, criado_em
    """
    ...

# Schema OpenAPI disponível em:
# GET /openapi.json
```

#### Schema OpenAPI Gerado
```json
{
  "openapi": "3.0.0",
  "info": { "title": "Portal InovaSkill API", "version": "1.0.0" },
  "paths": {
    "/v1/users/{user_id}": {
      "get": {
        "summary": "Get User",
        "parameters": [
          {
            "name": "user_id",
            "in": "path",
            "required": true,
            "schema": { "type": "integer" }
          }
        ],
        "responses": {
          "200": {
            "content": {
              "application/json": {
                "schema": { "$ref": "#/components/schemas/UserResponse" }
              }
            }
          }
        }
      }
    }
  },
  "components": {
    "schemas": {
      "UserResponse": {
        "type": "object",
        "properties": {
          "id": { "type": "integer" },
          "email": { "type": "string", "format": "email" },
          "name": { "type": "string" },
          "created_at": { "type": "string", "format": "date-time" }
        },
        "required": ["id", "email", "name", "created_at"]
      }
    }
  }
}
```

#### Frontend: Gerar Types TypeScript
```bash
# package.json
{
  "scripts": {
    "api:sync": "openapi-typescript http://localhost:8000/openapi.json -o src/api/generated.ts"
  }
}
```

```typescript
// src/api/generated.ts (GERADO AUTOMATICAMENTE)
// ⚠️ Nunca editar à mão
export interface UserResponse {
  id: number;
  email: string;
  name: string;
  created_at: string; // ISO 8601 datetime
}

export interface UserListResponse {
  items: UserResponse[];
  total: number;
  page: number;
}
```

```typescript
// src/services/userService.ts
import { UserResponse } from '@/api/generated';

export async function getUserById(id: number): Promise<UserResponse> {
  const response = await fetch(`/v1/users/${id}`);
  return response.json(); // TypeScript valida shape automaticamente
}
```

#### CI: Validação de Contrato
```yaml
# .github/workflows/api-contract.yml
name: API Contract Validation
on: [pull_request, push]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: pip install -e ".[dev]"
      - run: python -m pytest tests/openapi/  # Valida schema
      - run: npx openapi-typescript http://localhost:8000/openapi.json --output src/api/generated.ts
      - run: git diff --exit-code src/api/generated.ts
        # Falha se types gerados diferem de committed
```

#### Teste de Contract Breaking Change
```python
# tests/openapi/test_contract.py
def test_openapi_schema_valid():
    """Schema OpenAPI é válido"""
    schema = app.openapi()
    validate(instance=schema, schema=JSON_SCHEMA_DRAFT_7)

def test_no_breaking_changes_in_paths():
    """Nenhum campo obrigatório foi removido de response"""
    current = load_openapi_from_app()
    baseline = load_openapi_from_git("main")
    
    for path, methods in current.get("paths", {}).items():
        for method, details in methods.items():
            current_schema = details["responses"]["200"]["schema"]
            baseline_schema = baseline["paths"][path][method]["responses"]["200"]["schema"]
            
            # Campos obrigatórios do baseline devem existir em current
            required_fields = baseline_schema.get("required", [])
            assert all(f in current_schema.get("required", []) 
                      for f in required_fields), \
                f"Breaking change: {path} {method}"
```

### Checklist de Projeto
- [ ] FastAPI expõe `/openapi.json` com schema correto
- [ ] Docstrings FastAPI (""" ... """) preenchem descrição OpenAPI
- [ ] Frontend tem script `npm run api:sync` para gerar types
- [ ] Types TypeScript commitados ao repo
- [ ] CI falha se types gerados ≠ committed
- [ ] Versionamento de API: `/v1/`, `/v2/` para breaking changes
- [ ] Changelog/MIGRATE.md descreve breaking changes
- [ ] Pull requests que tocam API: generated types atualizados

---

## 5. Logging & Formato de Erro Padronizado
**Skill ID:** `structured-logging-errors`  
**Status:** Proposta | **Prioridade:** 🟠 Média  
**Tags:** observabilidade, logging, segurança, qualidade

### Propósito
Log estruturado (JSON, não strings soltas), nunca expor stack trace em produção, formato de erro consistente (`problem+json`), nunca logar PII/credenciais.

### Triggers
- Projeto novo com logs em string simples (`logger.info("User created")`)
- Erro retornando stack trace para cliente
- Log contendo email, CPF, ou token
- Observabilidade: precisam de `request_id` para trace distribuído
- Compliance: auditoria vê query secrets em log

### Regras Principais

#### ✅ Fazer
- Log estruturado: JSON com campos (`timestamp`, `level`, `message`, `context`)
- `request_id` em todo request (propagar em chamadas)
- Erro para cliente: `application/problem+json`, sem stack trace
- Erro em log: stack trace **completo** (só interno)
- Policy: logar contexto (user_id, endpoint), não PII
- Redação de log: nunca logar senha/token/email direto
- Nível de log apropriado: `ERROR` só para real error, `INFO` para flow

#### ❌ Nunca
- String simples em log: `logger.info("User created with password abc123")`
- Stack trace retornado em resposta HTTP para cliente
- Logar campo sensível sem [REDACTED]: `user.email: test@ex.com`
- `print()` em produção — só `logger`
- Nível de log errado: tudo como `ERROR`
- Erro genérico "Something went wrong" sem contexto

### Implementação

#### Structured Logging — Python + JSON
```python
# fastapi_app/logging_config.py
import json
import logging
from pythonjsonlogger import jsonlogger

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record['timestamp'] = record.created
        log_record['level'] = record.levelname
        log_record['logger'] = record.name

def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    handler = logging.StreamHandler()
    formatter = CustomJsonFormatter()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Uso
import logging
logger = logging.getLogger(__name__)

# ✅ CORRETO
logger.info("user_created", extra={
    "user_id": 123,
    "email": "[REDACTED]",  # Nunca plain email
    "request_id": "req_abc123",
    "duration_ms": 45
})

# ❌ ERRADO
logger.info(f"Created user {user.email} with password {user.password}")
```

#### Saída Estruturada
```json
{
  "timestamp": 1693478400.123,
  "level": "INFO",
  "logger": "fastapi_app.services.user_service",
  "message": "user_created",
  "user_id": 123,
  "email": "[REDACTED]",
  "request_id": "req_abc123",
  "duration_ms": 45
}
```

#### Erro Estruturado
```python
# fastapi_app/exceptions.py
from pydantic import BaseModel
from fastapi.responses import JSONResponse

class ProblemDetail(BaseModel):
    """RFC 7807: Problem Details for HTTP APIs"""
    type: str  # URI identificando o tipo de erro
    title: str  # Resumo curto
    status: int  # HTTP status
    detail: str  # Explicação específica (NÃO stack trace)
    instance: str  # URI da instância (request_id)

# Uso
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    logger.error("validation_error", extra={
        "error": str(exc),
        "request_id": request.state.request_id,
        "path": request.url.path,
        "stack_trace": traceback.format_exc()  # SÓ em log interno
    })
    
    return JSONResponse(
        status_code=400,
        content=ProblemDetail(
            type="https://api.example.com/errors/validation",
            title="Validation Error",
            status=400,
            detail="Provided email is invalid",  # Genérico para cliente
            instance=request.state.request_id
        ).dict(),
        media_type="application/problem+json"
    )
```

#### Middleware de Request ID
```python
# fastapi_app/middleware.py
import uuid
from starlette.middleware.base import BaseHTTPMiddleware

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        request.state.request_id = request_id
        
        logger.info("request_start", extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "user_agent": request.headers.get("user-agent")
        })
        
        response = await call_next(request)
        
        logger.info("request_end", extra={
            "request_id": request_id,
            "status": response.status_code,
            "duration_ms": (time.time() - request.state.start_time) * 1000
        })
        
        response.headers["x-request-id"] = request_id
        return response

app.add_middleware(RequestIDMiddleware)
```

#### Filtro de Redação (Nunca logar PII)
```python
# fastapi_app/log_filters.py
import re

class RedactionFilter(logging.Filter):
    """Remove PII e credenciais do log"""
    
    PATTERNS = {
        "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "cpf": r'\d{3}\.\d{3}\.\d{3}-\d{2}',
        "token": r'(Bearer|token)[\s:]+[A-Za-z0-9\._-]+',
        "password": r'(password|pwd)[\s:]*[^\s,}]+',
    }
    
    def filter(self, record):
        message = str(record.msg)
        for key, pattern in self.PATTERNS.items():
            message = re.sub(pattern, f'[REDACTED_{key.upper()}]', message)
        record.msg = message
        return True

logger.addFilter(RedactionFilter())
```

### Checklist de Projeto
- [ ] Logs em JSON estruturado (não strings simples)
- [ ] Cada request tem `request_id` único
- [ ] Erro retorna `application/problem+json`, sem stack trace
- [ ] Stack trace em log interno, não em resposta
- [ ] Policy: nunca logar email/CPF/token/senha diretamente
- [ ] Campos sensíveis marcados [REDACTED]
- [ ] Nível correto: ERROR para erro real, INFO para fluxo
- [ ] CI validar: nenhuma PII em logs (regex search)

---

## 6. LGPD & Privacidade de Dados
**Skill ID:** `lgpd-data-privacy`  
**Status:** Proposta | **Prioridade:** 🔴 Alta  
**Tags:** privacidade, compliance, lgpd, segurança, legal

### Propósito
Formalizar implementação de LGPD (Lei Geral de Proteção de Dados): consentimento documentado, direito ao esquecimento, anonimização de dados, nunca expor PII desnecessariamente. Alinha com seu PDI (plano de desenvolvimento individual).

### Contexto
Você está adaptando **apontamento**, **alimentto**, **menttosys**, e **Portal InovaSkill** para LGPD. Essa skill formaliza regras de engenharia que garantem compliance.

### Triggers
- Coleta de novo tipo de dado (email, CPF, foto, localização)
- Criação de endpoint que retorna dados de usuário
- Requisição de exclusão/anonimização de usuário
- Auditoria de compliance / preparação para externa
- Setup de novo projeto que coleta dados pessoais

### Regras Principais

#### ✅ Fazer
- Consentimento **explícito e documentado** antes de coletar: `consent_id` armazenado
- Coleta apenas o **mínimo necessário** (data minimization)
- Retenção: política clara — depois de quanto tempo deleta?
- Endpoint `DELETE /v1/users/{user_id}` (direito ao esquecimento)
- Anonimização reversível em audit/backups (criptografia, não deletion)
- Logging de acesso a dados sensíveis: quem viu, quando
- DPIA (Data Protection Impact Assessment) para processamento novo
- Termos de Privacidade **ativos e acessíveis**

#### ❌ Nunca
- Coletar CPF "porque alguém pediu" sem consentimento documentado
- Reter dados após exclusão (soft delete sem anonimização)
- Expor PII em erro/log/resposta API
- Compartilhar dados com terceiro sem consentimento
- "Ficou no backup" como desculpa para não deletar
- Deletar sem soft delete (manter histórico para auditoria)

### Implementação

#### Modelo de Consentimento
```python
# fastapi_app/models/consent_model.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean

class Consent(Base):
    """Registro de consentimento do titular"""
    __tablename__ = "consents"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    consent_type = Column(String)  # "personal_data", "marketing", "analytics"
    granted = Column(Boolean)  # True = consentimento dado, False = revogado
    created_at = Column(DateTime, default=datetime.utcnow)
    revoked_at = Column(DateTime, nullable=True)
    ip_address = Column(String)  # Prova de quem consentiu
    user_agent = Column(String)
    
class User(Base):
    """Usuário com soft delete e PII"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    email = Column(String, encrypted=True)  # Criptografado em repouso
    cpf = Column(String, encrypted=True)  # Nunca plain
    name = Column(String, encrypted=True)
    
    # LGPD
    deleted_at = Column(DateTime, nullable=True)  # Soft delete
    anonymized_at = Column(DateTime, nullable=True)  # Quando foi anonimizado
    consents = relationship("Consent", back_populates="user")
```

#### Coleta com Consentimento Explícito
```python
# fastapi_app/routes/auth.py
from fastapi import APIRouter, Request
from schemas import UserRegisterSchema
from services import UserService

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register")
async def register(
    user_data: UserRegisterSchema,
    request: Request,
    service: UserService = Depends()
):
    """
    Registra novo usuário com consentimento explícito.
    
    Requer: user_data.consent_to_terms = True
    Armazena: IP, User-Agent, timestamp para auditoria
    """
    if not user_data.consent_to_terms:
        raise HTTPException(
            status_code=400,
            detail="Consentimento aos termos é obrigatório"
        )
    
    # Cria usuário + registra consentimento
    user = service.register_user(
        user_data,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent")
    )
    
    logger.info("user_registered", extra={
        "user_id": user.id,
        "consent_id": user.consents[0].id,
        "request_id": request.state.request_id
    })
    
    return {"user_id": user.id, "message": "Registrado com sucesso"}
```

#### Direito ao Esquecimento
```python
# fastapi_app/routes/users.py
@router.delete("/v1/users/{user_id}/data")
async def delete_user_data(
    user_id: int,
    service: UserService = Depends(),
    request: Request = Request
):
    """
    Exclui dados do usuário (direito ao esquecimento).
    
    - Soft delete: marca como deleted_at
    - Anonimização: email, CPF, nome → [REDACTED]
    - Mantém histórico para auditoria (LGPD permite)
    """
    await service.anonymize_user(user_id)
    
    logger.info("user_data_deleted", extra={
        "user_id": user_id,
        "request_id": request.state.request_id,
        "timestamp": datetime.utcnow()
    })
    
    return {"message": "Dados excluídos com sucesso"}

# Implementação no service
async def anonymize_user(self, user_id: int):
    """Anonimiza dados pessoais do usuário"""
    user = self.repo.get_by_id(user_id)
    if not user:
        raise HTTPException(404, "Usuário não encontrado")
    
    # Soft delete + anonimização
    user.email = "[REDACTED]"
    user.cpf = "[REDACTED]"
    user.name = "[REDACTED]"
    user.deleted_at = datetime.utcnow()
    user.anonymized_at = datetime.utcnow()
    
    self.repo.save(user)
    
    # Deleta cookies, sessions
    await self.session_service.revoke_all_sessions(user_id)
```

#### Anonimização Reversível (Backup)
```python
# fastapi_app/tasks/backup_anonymization.py
"""
Backup anonimizado: dados real criptografados, backups com fields mascarados
"""
from cryptography.fernet import Fernet

def create_anonymized_backup(user_id: int):
    """Cria backup onde PII é substituído por hash"""
    user = get_user(user_id)
    
    backup = {
        "user_id": user.id,
        "email_hash": hash(user.email),  # Não reversível, só para auditoria
        "cpf_hash": hash(user.cpf),
        "created_at": user.created_at,
        "anonymized_at": datetime.utcnow()
        # ❌ Nada com PII real
    }
    
    # Salva backup (S3 com criptografia)
    s3.put_object(
        Bucket="backups",
        Key=f"anonymized/{user_id}_{datetime.now().isoformat()}.json",
        Body=json.dumps(backup),
        ServerSideEncryption="AES256"
    )
```

#### Política de Retenção
```python
# fastapi_app/tasks/data_retention.py
"""Exclui dados após período de retenção"""
from celery import shared_task
from datetime import datetime, timedelta

@shared_task
def purge_deleted_users():
    """
    Política: usuários deleted_at há mais de 90 dias são purgados
    Mantém soft delete por 90d para auditoria, depois purga definitivo
    """
    cutoff_date = datetime.utcnow() - timedelta(days=90)
    
    users_to_purge = User.query.filter(
        User.deleted_at < cutoff_date,
        User.deleted_at.isnot(None)
    ).all()
    
    for user in users_to_purge:
        logger.info("user_purged", extra={
            "user_id": user.id,
            "deleted_at": user.deleted_at,
            "purged_at": datetime.utcnow()
        })
        db.session.delete(user)
    
    db.session.commit()

# Agenda: diariamente às 2 AM
# celery beat: {"task": "purge_deleted_users", "schedule": crontab(hour=2)}
```

#### Auditoria de Acesso a PII
```python
# fastapi_app/models/audit_model.py
class AuditLog(Base):
    """Quem acessou dados sensíveis, quando"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True)
    accessor_id = Column(Integer, ForeignKey("users.id"))  # Admin/suporte
    subject_id = Column(Integer, ForeignKey("users.id"))  # Quem foi visto
    action = Column(String)  # "view_email", "view_cpf", "export_data"
    accessed_at = Column(DateTime, default=datetime.utcnow)
    reason = Column(String)  # "customer_support", "fraud_investigation"

# Middleware que log acesso
@app.get("/v1/users/{user_id}")
async def get_user(user_id: int, current_user = Depends(get_current_user)):
    """Qualquer acesso a dados sensíveis é auditado"""
    user = get_user_by_id(user_id)
    
    # Log de acesso
    audit.log_access(
        accessor_id=current_user.id,
        subject_id=user_id,
        action="view_user_profile",
        reason="admin_dashboard"
    )
    
    return user
```

#### Termos de Privacidade Versionados
```python
# fastapi_app/models/privacy_terms_model.py
class PrivacyTerms(Base):
    """Versão de termos de privacidade"""
    __tablename__ = "privacy_terms"
    
    id = Column(Integer, primary_key=True)
    version = Column(String, unique=True)  # "1.0", "1.1", "2.0"
    content = Column(Text)  # HTML/Markdown dos termos
    effective_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

class UserTermsAcceptance(Base):
    """Qual versão cada usuário aceitou"""
    __tablename__ = "user_terms_acceptance"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    terms_version = Column(String, ForeignKey("privacy_terms.version"))
    accepted_at = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String)

# Endpoint: GET /privacy/terms/current
@router.get("/privacy/terms/current")
async def get_current_privacy_terms():
    """Termos vigentes para novo usuário revisar"""
    return PrivacyTerms.query.order_by(
        PrivacyTerms.effective_date.desc()
    ).first()
```

### Checklist de Compliance
- [ ] Consentimento registrado antes de coletar qualquer PII
- [ ] Soft delete implementado (deleted_at, não deletion definitivo)
- [ ] Anonimização de PII após exclusão (email/cpf → [REDACTED])
- [ ] Política de retenção formalizada (ex: 90 dias → purga)
- [ ] Endpoint DELETE /users/{id}/data implementado
- [ ] Auditoria de acesso a dados sensíveis (quem viu, quando)
- [ ] Termos de Privacidade versionados e acessíveis
- [ ] Criptografia em repouso para PII (SQLAlchemy-encrypted)
- [ ] Nenhuma PII em logs/erro/trace
- [ ] DPIA (assessment) documentado para novo processamento
- [ ] Testes: verificam soft delete, anonimização, auditoria

---

## Matriz de Prioridade & Dependências

| Skill | Prioridade | Depende De | Benefício |
|-------|-----------|-------------|-----------|
| env-secrets-management | 🔴 Alta | Nenhuma | Evita vazamento de credenciais |
| dependency-security | 🔴 Alta | Nenhuma | Previne vulnerabilidades supply chain |
| lgpd-data-privacy | 🔴 Alta | Nenhuma | Compliance legal, projeto em adaptação |
| fastapi-layered-architecture | 🟠 Média | Nenhuma | Melhora TDD, testabilidade |
| api-contract-sync | 🟠 Média | fastapi-layered-architecture | Sincroniza backend/frontend |
| structured-logging-errors | 🟠 Média | env-secrets | Observabilidade, nunca logar secrets |

---

## Próximos Passos

1. **Validar escopo** com time (essas skills resolvem os problemas identificados?)
2. **Prototipo rápido**: Implementar LGPD + Env-Secrets em Portal InovaSkill primeiro
3. **Template de projeto**: Criar starter-kit FastAPI com essas 6 skills pré-configuradas
4. **Testes de compliance**: CI que valida cada regra (ex: nenhuma PII em logs)
5. **Documentação**: Runbook de "como onboarding novo dev com essas skills"
6. **Feedback loop**: Revisar após 2 semanas de uso em projeto real

---
