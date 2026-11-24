<p align="center">
  <img src="logo.png" alt="SysLink" width="96" />
</p>

<h1 align="center">SysLink</h1>

<p align="center">
  <strong>CRM + gerador de páginas de link na bio, com LLMs, RAG e Agentes de IA</strong><br/>
  <sub>Harness Engineering · LLMOps · LangChain</sub>
</p>

<p align="center">
  <a href="#-aviso-importante">⚠️ Aviso</a> ·
  <a href="#-o-que-está-funcionando">O que funciona</a> ·
  <a href="#-o-que-falta">O que falta</a> ·
  <a href="#-roadmap-curto">Roadmap</a> ·
  <a href="#-como-rodar">Como rodar</a>
</p>

---

## ⚠️ Aviso importante

**Isto é um projeto de estudo feito nas horas vagas.** Não é, e não pretende ser, um produto real para vender, hospedar em produção ou colocar na frente de clientes. Não há SLA, não há suporte, não há garantia de que qualquer coisa funcione amanhã — inclusive porque a API do Apify muda o contrato do actor sem avisar e já quebrou o projeto inteiro uma vez.

O objetivo é **aprender na prática** as partes chatas e importantes de um projeto de IA bem estruturado: filas, rate limit, cotas, mensageria, e-mails, guardrails em volta de LLM, observabilidade, testes e tudo mais que separa um script de um sistema. Aqui é onde essas ideias são testadas com calma, sem pressa e sem cobrança de cliente.

> Em resumo: **não é um produto, é um laboratório.** Se algo aqui te servir de base para algo seu, ótimo. Só não espere que esteja pronto para o mundo real.

---

## 📸 Telas

> **Prints a inserir** — espaço reservado para as imagens em `docs/screenshots/`.

| Login / Cadastro | Leads |
| :---: | :---: |
| ![Login](docs/screenshots/login.png) | ![Leads](docs/screenshots/leads.png) |

| Escavador | Gerador de bio |
| :---: | :---: |
| ![Escavador](docs/screenshots/escavador.png) | ![Gerador](docs/screenshots/gerador.png) |

| Abordagem (copiloto) |
| :---: |
| ![Abordagem](docs/screenshots/abordagem.png) |

---

## 🧭 O que é o SysLink

O SysLink é uma ferramenta para quem vende serviços pela internet (páginas de vendas, portfólios, sistemas, link trees) organizar o trabalho de prospecção e fechamento:

1. **Achar leads** — informar um nicho e o Escavador busca perfis reais no Instagram (Apify + Tavily em paralelo), classifica cada um com IA (produto provável, dificuldade, confiança) e entrega em cards prontos para aceitar ou rejeitar.
2. **Gerenciar funil** — cada lead aceito vira uma linha na tabela, com status, dificuldade, produto, último contato, motivo da perda e exportação em CSV.
3. **Gerar o site** — o Gerador monta a página de link na bio em tempo real (prévia ao vivo) e exporta o `index.html` pronto para publicar.
4. **Conduzir a conversa** — o copiloto de Abordagem recebe a mensagem do cliente e devolve a sugestão de resposta do vendedor, com raciocínio curto, sempre dentro do preço e do script configurados.

A ideia de longo prazo é transformar isso num sistema onde **agentes de IA** fazem parte do trabalho: escavar, classificar, sugerir abordagem, gerar o site e até publicá-lo — com RAG sobre o histórico de conversas e sobre o material de vendas. Hoje o caminho percorrido é metade disso; o resto está no roadmap.

---

## ✅ O que já funciona

### Aplicação

- [x] **Conta multi-usuário completa** — cadastro, confirmação de e-mail, login (JWT de 7 dias, bcrypt), esqueci/redefinir senha, reenviar confirmação. Cada usuário vê só os próprios dados.
- [x] **Tela de Leads** — CRUD completo, colunas ordenáveis, filtros, badges de status/dificuldade, modal de criação/edição, exclusão com confirmação e exportação CSV (`;` para o Excel pt-BR).
- [x] **Escavador de leads** — busca nicho no Instagram via Apify **e** Tavily em paralelo, com união em round-robin, deduplicação por `@username` e falha de uma fonte que não derruba a outra. Classificação por IA em chunks paralelos.
- [x] **Cota diária de escavação** — teto de perfis por usuário por dia (janela de calendário BRT), reserva **atômica** no banco (corrida entre requests não estoura o limite) e devolução da cota quando a busca falha ou entrega menos do que o pedido. Só o que foi **entregue** é cobrado.
- [x] **Gerador de página bio** — formulário + prévia em tempo real (iframe com debounce), seletor de ícones (lucide + simple-icons), cor/tema/nicho, e exportação do `index.html` completo. 100% client-side.
- [x] **Copiloto de Abordagem** — cola a mensagem do cliente, devolve raciocínio + mensagem pronta para copiar; abre já com a ficha do lead (`?lead=<id>`), injeta os dados do vendedor, guarda o histórico por lead e lista as conversas existentes.
- [x] **Guardrail determinístico de preço** — todo valor monetário citado pela IA (na mensagem **e** no raciocínio) é conferido contra o preço configurado; divergiu, a resposta é bloqueada. Sem preço configurado, qualquer valor citado é bloqueado.
- [x] **E-mails transacionais** (Resend) — confirmação de conta e recuperação de senha, com modo dev que loga o link quando não há chave configurada.
- [x] **Tema escuro (padrão) e claro** com alternância na sidebar e sem flash de hidratação.

### Engenharia

- [x] **Arquitetura em camadas** — `routes → services → repositories`, sem SQL nem regra de negócio na camada HTTP.
- [x] **Rate limit** — janela deslizante de 60s: **5 req/min por IP** nos endpoints públicos de auth e **100 req/min por usuário** nas rotas autenticadas, com `Retry-After` no 429.
- [x] **Erros padronizados RFC 7807** (`application/problem+json`) em **todos** os endpoints, com `request_id` no corpo para correlacionar com o log. Stack trace nunca vai para o cliente.
- [x] **Logging estruturado** — `structlog` em JSON, `RequestIDMiddleware` propagando `x-request-id`, redação de PII (senha, token, e-mail → `[REDACTED_*]`).
- [x] **Validação rígida** — schema Pydantic em todo endpoint (`extra="forbid"`), normalização de enums que vêm da IA, parser de JSON tolerante a retries e fallback de prosa.
- [x] **TDD** — **233 testes** no backend (pytest), cobrindo auth, rate limit, cota, escavador, settings, mensagens e guardrails. Os testes não dependem de rede nem de chave de API.
- [x] **Tipos gerados do OpenAPI** no frontend (`openapi-typescript`), lint/format com Biome.
- [x] **Docker Compose** com três serviços (`db`, `backend`, `frontend`), healthcheck no Postgres e volumes de dev com hot reload.
- [x] **Isolamento por usuário em toda query** — lead ou conversa de outro usuário devolve 404, sem vazar existência.

---

## ❌ O que falta

Nada abaixo está pronto; boa parte é intencional (é o que torna o projeto interessante de construir):

- [ ] **Filas / processamento assíncrono** — escavação, classificação e envio de e-mail rodam síncronos dentro da request. Falta uma fila de verdade (Redis + worker) para não amarrar o event loop nem o timeout do usuário.
- [ ] **Mensageria e notificações** — existe histórico de conversa, mas não existe notificação, webhook nem evento publicado para outros sistemas consumirem.
- [ ] **RAG de verdade** — hoje o "RAG" é um markdown inteiro lido no prompt e dado estruturado injetado (deliberadamente simples, sem embeddings nem retrieval). Falta base vetorial (pgvector) e busca semântica sobre histórico e material de vendas.
- [ ] **Agentes de IA / LangChain** — a orquestração é chamada direta à API da OpenRouter. Falta introduzir LangChain/LangGraph com agentes que executem passos (escavar → classificar → sugerir → gerar site) com ferramentas e estado.
- [ ] **Publicação dos sites** — o Gerador baixa um `index.html`; não há deploy, domínio nem hospedagem automatizada do site gerado.
- [ ] **Migrações de banco** — o Alembic está no `requirements` mas não está ligado; hoje o schema nasce do `create_all` + dois `ALTER TABLE` defensivos no lifespan.
- [ ] **CI/CD** — não há pipeline rodando lint, testes e build a cada push.
- [ ] **Observabilidade em produção** — Sentry e OpenTelemetry estão instrumentados como dependência, mas sem DSN configurado nem coleta ativa.
- [ ] **LGPD** — faltam consentimento explícito, direito ao esquecimento (`DELETE /users/{id}/data`), soft delete/anonimização, política de retenção e termos de privacidade.
- [ ] **Deploy** — roda só local via Docker Compose. Não há ambiente de produção.

---

## 🗺️ Roadmap curto

Ordem provável, sem promessa de prazo (nas horas vagas, lembra?):

| # | O que | Por quê |
|---|-------|---------|
| 1 | **Alembic ligado** (substituir `create_all`) | Sem isso qualquer mudança de schema em base existente quebra na mão |
| 2 | **CI no GitHub Actions** (Biome + pytest + build) | Proteger os 233 testes que já existem |
| 3 | **Fila para escavação e e-mails** (Redis + worker) | Tirar trabalho lento de dentro da request |
| 4 | **pgvector + retrieval** | RAG de verdade sobre histórico e script de vendas |
| 5 | **LangChain / LangGraph** com agentes e ferramentas | Escapar do "chama a API e reza" e virar orquestração com estado |
| 6 | **Gerar e publicar o site automaticamente** | Fechar o ciclo: lead → proposta → link no ar |
| 7 | **Sentry + painel de métricas de IA** (custo, latência, taxa de falha de formato) | LLMOps: enxergar o que a IA faz antes de confiar nela |
| 8 | **LGPD** (esquecimento, retenção, termos) | Obrigatório antes de qualquer coisa parecida com produção |

---

## 🛠 Como rodar

Requisitos: **Docker** e **Docker Compose**.

```bash
# 1. Clonar e entrar
git clone <repo-url>
cd SysLink

# 2. Configurar o ambiente
cp .env.example .env
# edite .env — no mínimo DB_*, SECRET_KEY e as chaves que quiser usar

# 3. Subir tudo (db + backend + frontend)
docker compose up -d --build

# 4. Abrir
# Frontend: http://localhost:3000
# API:      http://localhost:8000  (docs em /docs)
# Health:   http://localhost:8000/health
```

Sem chaves de API o sistema sobe mesmo assim: a busca usa só a fonte configurada, a classificação/IA cai com 502 amigável e os e-mails são logados no console no modo dev (com o link de confirmação, para você conseguir avançar).

### Testes

```bash
cd backend
pytest            # 233 testes, ~20s, sem rede e sem chaves
```

### Frontend

```bash
cd frontend
npm install
npm run dev       # http://localhost:3000
npm run lint      # Biome
npm run api:sync  # regera src/api/generated.ts a partir do OpenAPI
```

---

## 📚 Stack

| Camada | Tecnologia |
|--------|-----------|
| Frontend | **Next.js 15** (App Router) + **TypeScript** + React 19 |
| Backend | **FastAPI** (Python 3.12) em camadas `routes → services → repositories` |
| Banco | **PostgreSQL 16** |
| Orquestração | **Docker Compose** (db + backend + frontend) |
| IA | **OpenRouter** — Nemotron (chat, classificação e embeddings) |
| Scraping | **Apify** (`instagram-search-scraper`) |
| Busca web | **Tavily** (restrita a `instagram.com`, em paralelo à Apify) |
| E-mails | **Resend** |
| Auth | JWT (python-jose) + bcrypt (passlib) + verificação de e-mail |
| Logs / Erros | structlog (JSON) + `request_id` + RFC 7807 problem+json |
| Testes | **pytest** (TDD, 233 testes) |
| Lint / Format | **Biome** (frontend) |

**Planejado, ainda não usado:** LangChain / LangGraph (agentes), pgvector (RAG), Redis (filas), Alembic (migrações), Sentry (observabilidade).

---

## 🗂 Estrutura do projeto

```
SysLink/
├── docker-compose.yml       # db + backend + frontend
├── .env.example             # todas as variáveis documentadas
├── Contexto_IA.md           # documentação técnica detalhada (atualizada a cada mudança)
│
├── backend/
│   └── app/
│       ├── routes/          # só HTTP: validação e chamada de service
│       ├── services/        # regra de negócio (escavador, cota, copiloto, auth…)
│       ├── repositories/    # queries SQLAlchemy — sempre filtradas por user_id
│       ├── models/          # users, leads, daily_quotas, user_settings, messages
│       ├── schemas/         # schemas Pydantic de request/response
│       ├── dependencies/    # autenticação e rate limit
│       ├── exceptions/      # erros de negócio (quota, rate limit, conflito…)
│       └── prompts/         # contexto de vendas do copiloto
│   └── tests/               # 233 testes pytest
│
└── frontend/
    └── src/
        ├── app/(app)/       # leads, escavador, gerador, autenticado
        ├── app/(auth)/      # login, cadastro, confirmar, recuperar senha
        ├── api/             # cliente fetch + tipos gerados do OpenAPI
        ├── components/      # Sidebar, modais, badges, IconPicker…
        └── styles/          # tokens de tema (escuro/claro) + global
```

---

## 📖 Documentação

O arquivo [`Contexto_IA.md`](Contexto_IA.md) é a documentação técnica viva do projeto — stack, endpoints, decisões, gotchas e pendências, atualizada a cada mudança relevante. Se algo aqui estiver desatualizado, provavelmente ele está certo e este README não.

---

<p align="center">
  <sub>Projeto pessoal, feito nas horas vagas. Sem produto, sem SLA, sem promessa. Só curiosidade e café.</sub>
</p>
