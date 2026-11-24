# Contexto_IA.md — Documentação Técnica do Projeto SysLink

> Arquivo de contexto para IA — atualizar a cada mudança significativa na base do projeto.
> Última atualização: 2026-11-19 (v0.3.7 — travessões "—" removidos de TODO texto visível da UI, substituídos por ponto ou vírgula; comentários de código e o placeholder "—" das células vazias da tabela de Leads ficam como estão; textos internos de prompt (`prompts/abordagem.md`) mantidos; v0.3.6 — Abordagem: switch Config/Leads na coluna esquerda; painel lista as conversas com histórico (`GET /messages/conversations`) e o clique abre a conversa do lead ao lado via estado `leadId` + `?lead=` na URL; 233 testes backend passando)

---

## 1. Visão Geral

**SysLink** é um CRM de gestão de leads e funil de vendas. Tema **escuro minimalista** (cinza bem escuro + branco) como padrão, com alternância para **modo claro** pelo botão na sidebar.

| Camada | Tecnologia |
|--------|-----------|
| Frontend | Next.js 15 (App Router) + TypeScript |
| Backend | FastAPI (Python 3.12) |
| Banco | PostgreSQL 16 |
| Orquestração | Docker Compose (arquivo único na raiz) |
| Secrets | `.env` na raiz (nunca commitado) |
| Lint/Format | Biome (frontend) |
| Testes | Pytest (backend, TDD) |
| Navegação | Sidebar fixa (Leads / Escavador / Gerador / Abordagem) + alternador de tema + sair |
| Auth | Multi-usuário: JWT 7 dias (python-jose) + bcrypt (passlib) + verificação de e-mail via Resend |
| IA | OpenRouter — Nemotron (`nvidia/nemotron-3.5-lightning:free`) |
| Scraping | Apify — `apify/instagram-search-scraper` |
| Busca web | Tavily — `POST /search` restrito a `instagram.com` (Escavador, em paralelo à Apify) |
| Ícones | `lucide-react` (genéricos) + `simple-icons` (marcas) |

---

## 2. Estrutura de Diretórios

```
SysLink/
├── docker-compose.yml          # Orquestra db + backend + frontend
├── .env                        # Secrets (gitignored)
├── .env.example                # Placeholders documentados
├── .gitignore
├── Contexto_IA.md              # Este arquivo
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── app/
│   │   ├── main.py             # Ponto de entrada FastAPI
│   │   ├── config.py           # Settings via pydantic-settings
│   │   ├── database.py         # Engine + SessionLocal + Base
│   │   ├── middleware.py       # RequestIDMiddleware
│   │   ├── logging_config.py   # structlog JSON + RedactionFilter
│   │   ├── error_handlers.py   # Handlers RFC 7807 problem+json
│   │   ├── prompts/
│   │   │   └── abordagem.md    # Contexto de vendas do copiloto (lido INTEIRO p/ o prompt)
│   │   ├── routes/             # Camada HTTP (sem lógica de negócio)
│   │   │   ├── auth.py         # register/confirm/login/me/forgot/reset/resend
│   │   │   ├── leads.py        # CRUD de leads (exige Bearer via _get_service)
│   │   │   ├── excavator.py    # Escavador (exige Bearer no APIRouter)
│   │   │   ├── settings.py     # GET/PUT /settings (preço + dados do vendedor)
│   │   │   └── messages.py     # POST /reply + histórico do lead (GET/POST/DELETE) + GET /conversations
│   │   ├── services/
│   │   │   ├── auth_service.py # bcrypt + JWT + tokens de uso único
│   │   │   ├── email_service.py# Envio via Resend (confirmação/recuperação)
│   │   │   ├── lead_service.py
│   │   │   ├── quota_service.py # Cota diária de perfis escavados (janela BRT)
│   │   │   ├── excavator_service.py # Escavador: Apify + Tavily (paralelo) + classificação IA
│   │   │   ├── settings_service.py # Upsert das configurações (normaliza vazio→None)
│   │   │   └── message_service.py  # Copiloto: prompt + OpenRouter + guardrail de preço
│   │   ├── repositories/       # Acesso a dados (SQLAlchemy)
│   │   │   ├── user_repository.py
│   │   │   ├── quota_repository.py # Reserva atômica da cota (UPDATE condicional)
│   │   │   ├── lead_repository.py  # TODA query filtra por user_id
│   │   │   ├── message_repository.py # Histórico por lead (também filtra por user_id)
│   │   │   └── settings_repository.py # Linha única por user_id (upsert)
│   │   ├── models/             # users + leads (leads.user_id FK) + daily_quotas + user_settings + messages
│   │   ├── schemas/            # Schemas Pydantic
│   │   ├── dependencies/
│   │   │   ├── auth.py         # get_current_user (Bearer → User)
│   │   │   └── rate_limit.py   # RateLimiter (janela deslizante 60s) + rate_limit_auth/rate_limit_user
│   │   └── exceptions/         # BusinessLogicError, NotFoundError, ConflictError, RateLimitError, DailyQuotaError, etc.
│   └── tests/
│       ├── conftest.py         # client (AUTENTICADO), unauth_client, make_user… + fixture autouse que relaxa os rate limits
│       ├── test_auth.py        # 42 testes dos fluxos de auth
│       ├── test_rate_limit.py  # 21 testes de rate limit (unit + integração)
│       ├── test_health.py
│       ├── test_leads.py
│       ├── test_quota.py       # 14 testes da cota diária de escavação
│       ├── test_excavator.py    # 44 testes (busca, cota, Apify/Tavily, regressões de schema)
│       ├── test_settings.py    # 10 testes das configurações do usuário
│       └── test_messages.py    # 49 testes do copiloto + guardrail + histórico + conversas
│
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── biome.json              # Lint + format (substitui ESLint/Prettier)
    ├── tsconfig.json
    ├── next.config.js
    ├── public/                 # logo.png (sidebar) + logo.ico (favicon da aba)
    └── src/
        ├── app/
        │   ├── layout.tsx      # Root layout (html + tema; SEM sidebar)
        │   ├── page.tsx        # Redirect → /leads
        │   ├── (app)/          # Rotas AUTENTICADAS — route group (não muda URL)
        │   │   ├── layout.tsx  # AuthGuard + Sidebar + .appContent
        │   │   ├── leads/      # Tabela de leads (CRUD + CSV)
        │   │   ├── escavador/  # Escavador de leads via IA
        │   │   ├── gerador/    # Gerador de prompt
        │   │   └── abordagem/  # Copiloto de vendas (switch Config/Leads à esq. + chat à dir.)
        │   └── (auth)/         # Telas de auth — sem sidebar, centralizadas
        │       ├── layout.tsx  # GuestGuard (logado → /leads)
        │       ├── login/
        │       ├── cadastro/
        │       ├── confirmar/      # lê ?token= → POST /auth/confirm
        │       ├── esqueci-senha/
        │       ├── reenviar-confirmacao/ # POST /auth/resend-confirmation
        │       └── redefinir-senha/ # lê ?token= → POST /auth/reset
        ├── styles/
        │   ├── tokens.css      # Tokens de tema globais
        │   └── global.css      # Reset + importa tokens
        ├── api/
        │   ├── client.ts       # Fetch wrapper + CRUD + authApi + settingsApi + histórico (Bearer automático)
        │   ├── auth.ts         # Token no localStorage + 401 → /login
        │   ├── types.ts        # Enums e tipos do CRM
        │   ├── prompt.ts       # Template do prompt + buildPrompt()
        │   ├── excavator.ts    # Cliente da API do Escavador + toLeadCreate()
        │   ├── messages.ts     # Cliente da API de abordagem (generateReply)
        │   ├── index.ts        # Re-exporta tipos gerados
        │   └── generated.ts    # GERADO via openapi-typescript
        ├── components/
        │   ├── AuthGuard.tsx   # AuthGuard (sem token → /login) + GuestGuard
        │   ├── AuthCard.tsx    # Cartão central das telas de auth (+ module.css)
        │   ├── Sidebar.tsx     # Navegação + logo + tema + botão sair
        │   ├── LeadModal.tsx   # Modal criar/editar lead
        │   ├── ConfirmModal.tsx# Modal de confirmação (exclusão)
        │   ├── StatusBadge.tsx # Badge colorido de status
        │   ├── DificuldadeBadge.tsx
        │   ├── IconPicker.tsx  # Seletor de ícone por link (portal + lucide/simple-icons)
        │   └── Icons.tsx       # EditIcon, TrashIcon (SVG)
        └── styles/
            ├── tokens.css      # Tokens de tema globais (escuro + claro)
            └── global.css      # Reset + layout com sidebar
```

---

## 3. Domínio do CRM — Leads

### 3.1 Enumerações

| Campo | Valores |
|-------|---------|
| **Status** | `Não contatado`, `Aguardando resposta`, `Negociando`, `Negado`, `Fechado`, `Em desenvolvimento`, `Finalizado` |
| **Dificuldade** | `Fácil`, `Médio`, `Difícil` |
| **Produto** | `Portfólio`, `Página de vendas`, `Sistema`, `Link Tree` |

### 3.2 Campos do Lead

| Campo | Tipo | Obrigatório |
|-------|------|-------------|
| `nome` | string(255) | ✅ |
| `empresa` | string(255) | ❌ |
| `contato` | string(255) | ❌ |
| `instagram` | string(255) | ❌ |
| `produto` | enum | ✅ |
| `dificuldade` | enum | ✅ |
| `status` | enum | ✅ (default: `Não contatado`) |
| `motivo_perda` | text(2000) | ❌ |
| `ultimo_contato` | string(30) ISO 8601 | ❌ |
| `arquivos` | JSON array de strings | ✅ (default: `[]`) |

**Ordenação da tabela (tela de Leads):** colunas **Nome, Empresa, Produto, Dificuldade, Status e Último contato** são ordenáveis (asc/desc, uma por vez). Cada uma renderiza um `<button>` dentro do `<th aria-sort>` — teclado nativo (Enter/Espaço) e `aria-sort` corretos, sem `tabIndex`/`onKeyDown` manual (`lint/a11y/noNoninteractiveTabindex`). As demais colunas (Contato, Instagram, Motivo da perda, Arquivos, Ações) são fixas e não exibem cursor de ponteiro.

**Scroll da tela:** `.appContent` (global) é `height:100vh + overflow:hidden`, então **cada página cuida do próprio scroll**. Em `leads/page.module.css`, `.container` é `height:100vh; display:flex; flex-direction:column; overflow:hidden`, o header/filtros são `flex-shrink:0` e o `.tableWrapper` é `flex:1; min-height:0; overflow:auto` — a tabela é o único elemento com scroll e o `<thead>` é `position:sticky; top:0` (com `box-shadow: inset 0 -1px 0` no lugar de `border-bottom`, que some em `th` sticky com `border-collapse:collapse`).

### 3.3 Endpoints da API

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/api/v1/leads` | Cria lead (201) |
| `GET` | `/api/v1/leads` | Lista todos |
| `GET` | `/api/v1/leads/export` | Exporta CSV (text/csv) |
| `GET` | `/api/v1/leads/{id}` | Busca por ID (404 se não existe) |
| `PUT` | `/api/v1/leads/{id}` | Atualiza completo |
| `PATCH` | `/api/v1/leads/{id}` | Atualiza parcial |
| `DELETE` | `/api/v1/leads/{id}` | Remove (204) |

**Todos os endpoints acima exigem `Authorization: Bearer <JWT>`** (ver §3.9) — sem/inválido → 401 problem+json. As queries são filtradas por `user_id`: lead de outro usuário → **404** (não vaza existência).

### 3.4 Export CSV

- Rota: `GET /api/v1/leads/export`
- Formato: CSV com `;` como delimitador (compatível com Excel pt-BR)
- Colunas: Nome, Empresa, Contato, Instagram, Produto, Dificuldade, Status, Motivo da perda, Último contato, Arquivos
- Filename: `syslink_leads_YYYYMMDD_HHMMSS.csv`

### 3.5 Gerador de Página Bio (rota `/gerador`)

- **Função:** montar uma página link-in-bio e baixar o `index.html` pronto — 100% client-side, sem backend
- **Layout:** duas colunas — formulário à esquerda (440px) + **prévia em tempo real** à direita (iframe com `srcDoc`, debounce de 300 ms)
- **Campos do formulário:**
  - **Perfil:** Nome de exibição, @ do Instagram, Bio, URL da foto de perfil, Ícone da aba (favicon — se vazio, usa a foto)
  - **Links:** lista dinâmica (adicionar/remover) com título, subtítulo, URL e **ícone por link**
  - **Redes sociais:** Instagram, TikTok
  - **Mídia:** vídeo do YouTube (opcional)
  - **Visual:** cor de destaque (swatch + hex + paleta derivada), tema (Auto/Claro/Escuro), nicho (dispara o layout "fitness")
- **Ícones — `frontend/src/components/IconPicker.tsx`:**
  - 28 genéricos via **lucide-react** + 16 marcas via **simple-icons** (LinkedIn usa path local — removido do simple-icons)
  - Busca por nome + cor do ícone (destaque / branco / preto)
  - O dropdown é renderizado com `createPortal` em `<body>` + `position: fixed` — escapa do `overflow: hidden` de `.linkRow`/`.formScroll` (sem isso nada aparece)
  - `getIconSvg()` devolve o SVG string do HTML exportado (`renderToStaticMarkup` para lucide, `path` do simple-icons para marcas)
- **Geração do HTML:** `generateHTML(profile, scheme, fitness)` em `frontend/src/app/gerador/page.tsx` monta o arquivo estático completo
  - Fonte do nome de exibição: **Outfit 600** (`--display`, `font-weight: 600`, `clamp(34px,9vw,46px)`), carregada no Google Fonts junto com Inter
- **Ações:**
  - `Adicionar Link` / `Remover link` → gerencia a lista de botões
  - Campos, cor, tema e nicho → atualizam a prévia
  - `Baixar index.html` → exporta o arquivo (o botão confirma o download por ~2,2 s)
- **Template de prompt:** `frontend/src/api/prompt.ts` mantém `PROMPT_TEMPLATE` (modelo HTML completo embutido) e `buildPrompt(fields)` com placeholders `{{INSTAGRAM}}`, `{{NOME}}`, `{{BIO}}`, `{{LINKS}}`, `{{TIKTOK}}`, `{{VIDEO}}`, `{{FOTO}}`, `{{FAVICON}}`, `{{COR}}`, `{{TEMA}}` — hoje **não está ligado à UI** (mantido como template exportável)

### 3.6 Escavador (rota `/escavador`)

- **Função:** buscar leads reais no Instagram — informar nicho, encontrar perfis
- **Fonte de dados:** **Apify + Tavily em paralelo** — dois caminhos para achar perfis REAIS:
  - `_search_profiles()` agenda só as fontes com chave configurada e roda todas juntas (`asyncio.gather(return_exceptions=True)`; Apify vai para `run_in_threadpool`, Tavily é `httpx` async);
  - os resultados são unidos em **round-robin** (`Apify[0], Tavily[0], Apify[1], Tavily[1]…`) e **deduplicados por `@username`**, com teto em `quantidade` — a alternância evita que a Apify, ao já devolver `quantidade` perfis, esconda todos os do Tavily;
  - **falha em UMA fonte não derruba a busca:** log `search_source_failed` + resposta com os resultados parciais da outra (sem 502). Só erro nas DUAS vira 502 citando as fontes; **nenhuma chave** → 502 `"APIFY_API_TOKEN e TAVILY_API_KEY não configuradas no .env"`.
- **Apify:** `apify/instagram-search-scraper` — scraping de perfis (bio, seguidores, categoria, verificado, negócio). Sem `APIFY_API_TOKEN` a fonte nem é chamada.
  - **Input do actor (contrato volátil):** `{"search": nicho, "searchType": "user", "searchLimit": min(count, 250)}`. A Apify **atualiza o schema do actor sem avisar** — em 2026-11-17 `searchType` deixou de aceitar `"profiles"` e passou a exigir `"place" | "user" | "hashtag" | "popular"`, devolvendo **400** `Input is not valid: Field input.searchType must be equal to one of the allowed values` → todo `/excavate` virava 502. **`searchType: "user"` = perfis.** Teste de regressão: `TestApifyRunInput` (`test_excavator.py`) monkeypatcha o `ApifyClient` e valida o `run_input` exato + o teto de 250. Não ligar `enhanceUserSearchWithFacebookPage` (risco LGPD, já discutido no projeto).
- **`null` nas fontes (regressão v0.3.1):** `dict.get(chave, default)` **não cobre valor `null`** — o default só vale para chave AUSENTE. A Apify passou a enviar `businessCategoryName: null` (entre outros) e o `None` vazava para o `ExcavateResponse` (`categoria: str`) → **500** na montagem da resposta, mesmo com a busca tendo dado certo. A montagem em `excavator_service.excavate` usa `or`/checagem explícita em TODOS os campos (`seguidores`, `bio`, `categoria`, `verificado`, `negocio`, `url`, `produto`, `dificuldade`, `confianca`) e `nome` cai para o username. Teste: `TestNullFieldsFromSources`.
- **Variáveis de ambiente mudaram? RE-CRIAR o container:** `docker compose restart` **não re-interpola** o `.env` — ele só reinicia o processo. Container criado antes de uma chave existir fica **sem ela para sempre** (ex.: `TAVILY_API_KEY` vazia no container = fonte nem é agendada, sem nenhum log de erro). Use `docker compose up -d backend` (recreate) e confira com `docker exec syslink_backend printenv NOME_DA_VAR`.
- **Tavily:** `POST https://api.tavily.com/search` com `include_domains: ["instagram.com"]` + `include_domains_mode: "restrict"` (filtro duro), `search_depth: "basic"` (1 crédito), `max_results: min(quantidade, 20)` — **teto da API** — e timeout de 30 s no httpx compartilhado. Só entram URLs de perfil de um segmento (`instagram.com/{user}/`): `/p/`, `/reel/`, `/explore/`, subcaminhos e outros domínios são descartados. Do title/conteúdo são extraídos **nome** (texto antes de `(@user)`), **seguidores** (`1,5K`→1500, `1,512`→1512, `12.500`→12500) e **bio** (a meta description `1,512 Followers, … (@user)` é removida). Perfis Tavily vêm sem `categoria`/`verificado`/`negócio` (defaults falsos) — a classificação IA compensa.
- **Classificação:** IA via OpenRouter (`nvidia/nemotron-3.5-lightning:free`) atribui produto, dificuldade e confiança — perfis fatiados em **chunks de 15** (`CLASSIFY_CHUNK_SIZE`) e classificados **em paralelo** com `asyncio.gather` (menos latência, resposta menos propensa a truncar no `max_tokens`); falha em um chunk deixa só aquele trecho com os defaults, sem derrubar os demais (teto: `CLASSIFY_MAX_PROFILES = 50`)
- **Config:** `APIFY_API_TOKEN`, `APIFY_ACTOR_ID`, `TAVILY_API_KEY`, `OPENROUTER_API_KEY`, `EXCAVATE_DAILY_PROFILE_LIMIT` no `.env`
- **Cota de perfis escavados (NOVA, v0.2.2):** **máximo 50 perfis entregues por usuário por dia** (`EXCAVATE_DAILY_PROFILE_LIMIT`, default 50; `0` desativa) — janela de **calendário BRT** (00:00–24:00 UTC-3, offset fixo `BRT = timezone(timedelta(hours=-3))`, sem depender de tzdata), guardada na tabela `daily_quotas` (linha única por `user_id` + `day`, criada no `create_all` do lifespan — **não vive em memória**, sobrevive a restart do container):
  - **Reserva ANTES da busca:** a rota reserva `quantidade` (`QuotaService.reserve`) e, se a busca falhar (502/504) ou encontrar menos perfis que o pedido, devolve a diferença (`release`) — **falha de serviço nunca consome cota**; só o **entregue** é cobrado;
  - **Atômica:** o `reserve` é um `UPDATE … WHERE profiles_used + n <= limite` (comparação DENTRO do SQL) → requisições simultâneas não ultrapassam o teto; corrida de criação da linha do dia é resolvida por `IntegrityError` + retry;
  - **Esgotou → 429** `DailyQuotaError` (herda de `RateLimitError`) com header `Retry-After` (segundos até a meia-noite BRT) e mensagem PT-BR `"Cota diária de 50 perfis escavados atingida. A cota renova em ~Xh/Ymin."`; request acima do que resta é **rebaixado** para o que falta (entrega parcial, não erro);
  - **Consulta:** `GET /api/v1/excavate/quota` → `{ ativa, limite, usado, restante, renova_em }` (`renova_em` = ISO 8601 da próxima meia-noite BRT) — a UI mostra o badge `Cota: X/50 hoje` no header, desabilita o botão em 0 e o `POST /excavate` devolve o mesmo objeto em `cota` (o indicador atualiza sem refetch);
  - **Isolamento:** a cota é por `user_id` (o repositório recebe o id do usuário autenticado) — um usuário esgotado não afeta os demais.
- **Rate limit por usuário:** `rate_limit_user` cobre `/excavate` (e `/leads`) com **100 req/min por `user_id`** (§3.9) — é um limite de *frequência*, distinto da cota diária de *volume* acima; não existe limite mensal/credito de buscas. O custo por busca é do próprio plano: Apify ~US$2,70/1000 resultados + 1 crédito Tavily por escavação (≤20 resultados).
- **Endpoint:** `POST /api/v1/excavate` → `{ nicho, quantidade }` → `{ resultados: [...], cota: { ativa, limite, usado, restante, renova_em } }`
- **Endpoint:** `GET /api/v1/excavate/quota` → `{ ativa, limite, usado, restante, renova_em }`
- **Endpoint:** `POST /api/v1/embed` → `{ text }` → `{ embedding, dimensions }`
- **Dados retornados por resultado:**
  - `instagram`, `nome`, `empresa`, `contato` — dados do perfil
  - `produto`, `dificuldade`, `confianca` — classificação da IA
  - `seguidores`, `bio`, `categoria`, `verificado`, `negocio`, `url` — dados reais da fonte (Apify e/ou Tavily)
- **Fluxo:**
  1. Usuário digita nicho + quantidade (10/20/30/50)
  2. Backend reserva a cota do dia → 429 se esgotada
  3. Backend chama Apify + Tavily em paralelo → busca perfis reais (filtra privados)
  4. IA classifica cada perfil (produto, dificuldade, confiança) e a cota é ajustada ao que foi entregue
  5. Usuário vê cards com dados reais + link clicável para o Instagram + badge de cota atualizado
  6. **Aceita** (cria lead na tabela) ou **rejeita** (descarta)
  - **Aceitar todos:** `handleAcceptAll` envia os POSTs em **lote de 5** (`ACCEPT_CHUNK_SIZE`) com `Promise.allSettled` — um lote falhar não derruba os demais; card só ganha ✓ se o POST deu certo; botão fica "Adicionando..." (com os botões de ação desabilitados para não duplicar) e falhas viram banner "X de Y não puderam ser adicionados."
- **Validação Pydantic:** `ExcavateRequest` com `extra="forbid"`, nicho 1–500 chars, quantidade 1–50
- **Falhas:** fonte que falha sozinha → 502 com mensagem segura (detalhe técnico só no log `search_source_failed`); fonte que falha com a outra em pé → busca segue com o que sobrou; busca > 180 s → 504 (ver §3.8)
- **Custo Apify:** $2.70/1000 resultados (free plan com $5 crédito)
- **Scroll da tela:** mesmo padrão da tela de Leads (`.appContent` global é `overflow:hidden`) — `escavador/page.module.css` tem `.container` em `height:100vh; flex column; overflow:hidden`, header/form/resumo com `flex-shrink:0` e `.resultsList` em `flex:1; min-height:0; overflow-y:auto`. Header + formulário ficam fixos e só a lista de cards rola.

### 3.7 Tema (Escuro padrão + Claro)

O tema vive em `frontend/src/styles/tokens.css` — sem CSS inline e sem cor solta em componente:
- **Padrão: ESCURO** (visual original preservado): fundo `#0d0d0f` (base), `#161618` (secondary), `#1e1e22` (tertiary); texto `#f0f0f0` / `#a0a0a8` / `#6e6e76`
- **Primária (verde moderno):** `#10b981` no escuro com texto escuro por cima (`#04140d`, contraste AA) e `#047857` no claro com texto branco — tokens `--color-primary`, `-hover`, `-muted`, `-contrast`, `-ring`, `-glow`
- **Modo claro:** bloco `[data-theme="light"]` no fim do `tokens.css` sobrescreve fundo, texto, bordas, status, dificuldade, semânticas e sombras
- **Badges de status** e **dificuldade** têm cores próprias por tema (ver tokens)
- **Alternador:** botão Sol/Lua no rodapé da `Sidebar.tsx` — grava `localStorage["syslink-theme"]` e seta/remove `data-theme` no `<html>` (o escuro é o padrão, sem atributo)
- **Sem flash:** script inline em `layout.tsx` com `strategy="beforeInteractive"` aplica `data-theme="light"` antes da primeira pintura; o `<html>` usa `suppressHydrationWarning` para a hidratação não reclamar
- **Regra:** cor de tema só por token — hex fixo em CSS de componente precisa migrar para `tokens.css`
- **Logo e favicon:** a sidebar exibe `<img src="/logo.png" className={styles.logo}>` (32×32px) e a aba do navegador usa `metadata.icons: { icon: "/logo.ico" }` no `layout.tsx` — ambos servidos de `frontend/public/`. **Gotcha:** o Next.js não resolve `import ... from "*.png"` vindo de `src/` (erro `Module not found`); imagens estáticas vão para `public/` e são referenciadas por caminho público `/arquivo`.

### 3.8 Tratamento de Erros (RFC 7807)

Padrão único em **todos** os endpoints — corpo `application/problem+json`:

```json
{ "type": "https://syslink.com/errors/<status>", "title": "...",
  "status": <status>, "detail": "mensagem PT-BR", "instance": "<request_id>" }
```

- **Handlers globais** em `backend/app/error_handlers.py`:
  - `StarletteHTTPException` → 400/401/403/404/405/409/502/504 com `detail` string;
  - `RequestValidationError` (422 do Pydantic) → **também problem+json** com `detail` string (ex.: `"nome: conteúdo curto demais; produto: campo obrigatório"`) + `errors[]` (`field`/`type`/`message` em PT-BR via `_VALIDATION_MESSAGES`). Sem este handler o FastAPI devolve `{"detail": [...]}` (lista) e o frontend exibia `[object Object]`;
  - `Exception` não tratada → 500 com detail genérico (`"Ocorreu um erro interno. Tente novamente."`) — **stack trace só no log**, nunca no cliente (teste `assert "stack" not in body`).
- **Mensagens:** sempre PT-BR para o usuário; detalhe técnico (URL, status, corpo cru de serviço externo) fica no log com `request_id`.
- **Serviços externos:** `ExternalServiceError(RuntimeError)` em `app/exceptions/` carrega só texto seguro — `excavator_service` captura qualquer exceção do Apify, loga `stack_trace` e relança com mensagem amigável; a rota converte em 502. Token ausente → 502 `APIFY_API_TOKEN não configurada no .env`.
- **Escavador:** `client.actor(...).call()` é síncrono → roda em `run_in_threadpool` (não trava o event loop/`/health`); busca completa limitada por `asyncio.wait_for(EXCAVATE_TIMEOUT_SECONDS=180)` → **504** se estourar.
- **429:** dois erros herdam de `RateLimitError(HTTPException)` → problem+json + header `Retry-After` — o de **rate limit** (100 req/min, mensagem "Muitas tentativas…") e o `DailyQuotaError` da **cota diária** do Escavador (mensagem "Cota diária de 50 perfis escavados atingida…", `Retry-After` em segundos até a meia-noite BRT).
- **OpenRouter:** embed e classificação usam um `httpx.AsyncClient` **compartilhado por processo** (`get_http_client()` em `excavator_service` — reuso de conexão, um client novo por request antes) com timeout por chamada (`EMBED_TIMEOUT_SECONDS=30` / `CLASSIFY_TIMEOUT_SECONDS=60`); fechado no shutdown por `close_http_client()` no `lifespan` de `main.py`.
- **Frontend** (`src/api/client.ts`): `problemMessage()` converte problem+json (string, `errors[]` ou lista legada) em mensagem PT-BR; fallback por status (`STATUS_MESSAGES`); falha de rede → `"Não foi possível conectar ao servidor. Verifique se a API está no ar."` (nunca `Failed to fetch`). Erros aparecem em banner com ✕ ou inline no modal — **zero `alert()`**.
- **Request ID:** `x-request-id` em toda resposta; `instance` do problem+json é o mesmo id → rastreio no log.

### 3.9 Autenticação (multi-usuário + JWT)

**Modelo:** tabela `users` (email único, `password_hash` bcrypt, `email_verified`, tokens de confirmação/recuperação) + `leads.user_id` (FK) — cada usuário vê/edita **só os próprios leads** (filtro aplicado em todo `LeadRepository._scoped()`).

**Endpoints `/api/v1/auth/*`** (única família pública — `/health` também é aberto):

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/register` | Cria conta (201) e envia e-mail de confirmação; e-mail duplicado → **409** |
| `POST` | `/confirm` | Confirma e-mail com o token do link (200; inválido/expirado → 400; uso único) |
| `POST` | `/login` | E-mail+senha → JWT (401 credenciais; 403 e-mail não confirmado) |
| `GET` | `/me` | Dados do usuário autenticado (401 sem token/inválido/expirado) |
| `POST` | `/forgot` | Envia link de redefinição — **sempre 202 com resposta genérica** |
| `POST` | `/resend-confirmation` | Reenvia e-mail de conta pendente (202 genérico) |
| `POST` | `/reset` | Redefine senha com o token (uso único, validade 1h) |

**Fluxo:** `register` → Resend → link `{FRONTEND_URL}/confirmar?token=…` → `confirm` → `login` → JWT (`sub=user_id`, HS256 com `SECRET_KEY`, 7 dias) → header `Authorization: Bearer <token>`.

**Decisões e gotchas:**
- **Sem `RESEND_API_KEY`/`RESEND_FROM` o envio é IGNORADO com warning no log** (modo dev) — o cadastro não quebra; além do warning, **o link completo é logado** (`verification_link_dev_only` / `reset_link_dev_only`) para poder confirmar/redefinir sem servidor de e-mail. Nunca loga o link quando o Resend está configurado.
- **Falha de serviço externo → 502 problem+json** (`ExternalServiceError` handler em `error_handlers.py`, `detail` = texto seguro da exceção). Sem o handler a exceção caía no genérico e virava 500 "erro interno" enganoso. No `register`, a conta é criada ANTES do envio → se o envio falhar, o retry devolve **409** e a saída é `/reenviar-confirmacao` (o frontend mostra o atalho no 409 do cadastro e no 403 do login).
- **`bcrypt==4.0.1` está PINADO no `requirements.txt`** — passlib 1.7.4 quebra com bcrypt ≥4.1 (`detect_wrap_bug` → `ValueError: password cannot be longer than 72 bytes` em TODO hash → 500 no register/login). A versão pinada é a mesma validada localmente.
- **`RESEND_FROM` precisa de domínio verificado no Resend** — remetente `@gmail.com` → API responde **403** "domain is not verified". O `.env` está com **`SysLink <onboarding@resend.dev>`** (formato com display name aceito; entrega APENAS no e-mail da conta Resend — para produção, verificar domínio próprio em resend.com/domains).
- Tokens de e-mail: `secrets.token_urlsafe(32)` (43 chars), validade **24h** (confirmação) / **1h** (reset), armazenados em claro no `users` (são opacos, aleatórios e de uso único — hashear não protegeria nada) e **limpos ao serem consumidos**.
- **Anti-enumeração:** `login` devolve a mesma mensagem `"E-mail ou senha incorretos"` para senha errada e e-mail inexistente; `/forgot` e `/resend-confirmation` respondem sempre igual, exista conta ou não.
- `get_current_user` (`app/dependencies/auth.py`) → 401 problem+json PT-BR para: header ausente, formato ≠ `Bearer`, token inválido/expirado ou usuário removido.
- Proteção: leads via dependência no `_get_service` da rota (que também passa o `user_id` ao repository); Escavador via `dependencies=[Depends(get_current_user)]` no `APIRouter`.
- **Migração de banco:** `create_all` não altera tabela existente → `_ensure_lead_user_column()` no `lifespan` faz `ALTER TABLE leads ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id)` (só Postgres; SQLite dos testes já nasce com a coluna). **Leads antigos ficam com `user_id NULL` e não aparecem em nenhuma listagem** — resgate manual: `UPDATE leads SET user_id = <id>;`.
- **Frontend:** token em `localStorage["syslink-token"]` (`src/api/auth.ts`); `client.ts` e `excavator.ts` anexam o Bearer em todo request e, em **401 fora de `/api/v1/auth/*`**, limpam a sessão e redirecionam para `/login`. Rotas protegidas: `AuthGuard` no layout `(app)`; telas de auth: `GuestGuard` no layout `(auth)`. Erros da API viram `ApiError` (com `status`) → 409 no cadastro e 403 no login exibem atalho para `/reenviar-confirmacao`.
- **Gotcha Next:** `useSearchParams` exige `<Suspense>` no build — páginas `/confirmar` e `/redefinir-senha` envelopam o conteúdo.
- **Rate limit (TDD, `app/dependencies/rate_limit.py`):** janela deslizante de 60s **em memória** (`RateLimiter` com `time.monotonic` + `threading.Lock`; zera no reinício do container). Dois escopos: **`rate_limit_auth`** → balde único `auth:{ip}` nos 6 endpoints **públicos** de auth (login/register/confirm/forgot/resend-confirmation/reset; `/me` é isento) com **5 req/min**; **`rate_limit_user`** → balde `user:{id}` em **todos** os endpoints de `/leads` e `/excavate` com **100 req/min**. Estourou → **429 problem+json PT-BR** ("Muitas tentativas. Tente novamente em N segundos.") + header **`Retry-After`** (encaminhado pelo `http_exception_handler` via `exc.headers`). `RATE_LIMIT_*_PER_MINUTE=0` desativa; `TRUST_PROXY_HEADERS=false` (default) **ignora `X-Forwarded-For`** (anti-spoof) — só ligar atrás de proxy confiável. **Gotcha Docker:** sem proxy, todos os clients aparecem com o mesmo IP (ex.: `172.19.0.1`) → na prática o limite de auth vira **global**; a suíte usa fixture autouse que relaxa os limites para 100_000 e zera o limiter por teste.

---

### 3.10 Abordagem (rota `/abordagem`) — copiloto de vendas

- **Função:** o vendedor cola a mensagem do CLIENTE e a IA devolve a próxima mensagem do vendedor (raciocínio curto + texto pronto para copiar). Tela em duas colunas: **configuração à esquerda** (preço, nome, empresa, tom de voz) + **chat à direita** (histórico Cliente/Sugestão com botão Copiar e "Nova conversa"). **Não é chatbot com o cliente** — quem envia é o vendedor.
- **Novo recurso — botão "Enviar mensagem" por lead:** cada row da tabela de leads tem um ícone de mensagem `💬` que, ao ser clicado, abre `/abordagem?lead=<id>`. O backend carrega a ficha completa do lead (nome, empresa, instagram, contato, produto, dificuldade, status, último contato) via `LeadRepository` (já filtrado por `user_id`). A ficha é injetada no system prompt via `render_lead_block()` — a IA sabe exatamente com quem está falando e o contexto começa com "DADOS DO LEAD". Se o `lead_id` for inválido, não pertencer ao usuário ou não existir → **404** (não pode ser spoofed). O chip no topo do header mostra "Carregando lead..." enquanto a busca roda; ao carregar, exibe o nome/empresa do lead.
- **Arquitetura do "RAG" — deliberadamente simples (sem pgvector, sem embeddings):**
  - a base é **1 produto + 1 script** → `backend/app/prompts/abordagem.md` (produto, etapas da abordagem, objeções, tom, regra de ouro) é lido **INTEIRO** no system prompt (`_load_context()` com `lru_cache`) — fatiar e buscar só adicionaria falha de retrieval;
  - preço/nome/empresa/tom são **dado estruturado**: vivem em `user_settings` e são **injetados** no bloco `DADOS DO VENDEDOR` (`render_system_prompt()`), nunca "buscados" pela IA — injeção não tem etapa que devolva valor desatualizado;
  - **guardrail determinístico pós-geração:** `extract_prices()` / `assert_prices_ok()` comparam TODO valor monetário (`R$ 97`, `1.200,00`, `97 reais`) de `mensagem` **e** `raciocinio` com o preço configurado — divergiu → `ExternalServiceError` (502) em vez de mensagem errada; **sem preço configurado, qualquer valor citado é bloqueado**;
  - saída JSON `{"raciocinio", "mensagem"}` com parse tolerante a ```` ```json ```` (mesmo padrão da classificação do Escavador); `temperature 0.4`, `max_tokens 1200`, `reasoning` desabilitado.
- **Novo recurso — `lead_id` no `POST /api/v1/messages/reply`:** o payload agora aceita opcionalmente `lead_id`. Quando informado, o `MessageService` (que recebe `LeadRepository` já escopado por `user_id`) carrega a ficha e a injeta no prompt. `lead_id` alheio → 404; `lead_id` inexistente → 404; tipo int `ge=1`, `extra="forbid"` no schema (tipos não-inteiros ou zero são 422).
- **Parser tolerante de JSON (v0.3.3 — corrige "resposta em formato inválido" na 2ª mensagem):** `_parse_reply` antes exigia exatamente `{"raciocinio", "mensagem"}` com JSON limpo — o modelo Nemotron às vezes devolve texto ao redor, chaves alternativas ou estrutura aninhada e o 2º request do chat falhava. Agora o parser: (1) remove cercas de ```` ``` ````; (2) tenta `json.loads` no primeiro bloco `{...}`; (3) se falhar, acha o bloco `{...}` **balanceado por profundidade** (regex recursiva `(?R)` não existe no `re` do Python — `PatternError`); (4) extrai `raciocinio`/`mensagem` de chaves alternativas (`pensamento`, `thinking`, `resposta`, `texto`…); (5) fallback: maior string do objeto vira `mensagem`. Só se nada funcionar → 502 "formato inválido".
- **Retry + fallback de prosa (v0.3.4 — corrige a causa raiz restante):** o diagnóstico em produção mostrou que o modelo às vezes ignora o formato e devolve **prosa pura sem nenhum `{`** (log `reply_format_retry`, `tem_json: false`) — nenhuma técnica de parsing resolve isso. Agora `reply()`: (1) tenta `_parse_reply`; (2) em falha, reenvia **uma vez** com `_FORMAT_REMINDER` acrescentado ao system prompt ("LEMBRETE: … responda SOMENTE com o objeto JSON…"); (3) se ainda assim falhar, `_prose_fallback` aceita a prosa como `mensagem` (com `raciocinio` vazio) **desde que não comece com `{`** — JSON truncado nunca vira fala pronta; vazio ou >4000 chars → 502. O guardrail de preço continua rodando em cima do resultado nos dois caminhos. Coberto por 3 testes novos (`test_broken_json_returns_502_even_after_retry`, `test_pure_prose_is_retried_with_format_reminder`, `test_pure_prose_after_retry_becomes_the_message`); `fake_chat` agora aceita lista de respostas (uma por chamada) e expõe `captured["calls"]`.
- **Conftest não toca no Postgres externo (v0.3.4):** o lifespan do `TestClient` rodava `create_all` contra `DATABASE_URL` real (`localhost:5432`) — ~2,2s de setup por teste quando outro Postgres escuta na porta (suíte foi de 16s para 6min). Fixture autouse `_lifespan_uses_test_db` faz monkeypatch de `app.main.engine` para o SQLite de teste. Suíte volta a ~16s.
- **Mensagem inicial automática (v0.3.3):** quando o lead carrega via `?lead=<id>`, a página insere sozinha a 1ª fala do cliente no chat (`Olá, {nome}! Vi seu perfil…`) — a conversa já começa com contexto em vez de tela vazia. `handleReset` ("Nova conversa") **restaura** essa mensagem se ainda houver lead acoplado; sem lead, o chat volta vazio. A entrada é criada só se o histórico estiver vazio (nunca sobrescreve conversa em andamento).
- **Toggle mostrar/ocultar configuração (v0.3.3):** `showConfig` no estado da página; o botão ("Ocultar config"/"Mostrar config") fica **fora** do `<aside>` condicional — dentro dele sumiria junto com o painel e o usuário não conseguiria reabrir. Layout: `{showConfig && <aside>…</aside>}` + `<section>` do chat sempre visível; o texto do estado vazio do chat muda conforme o toggle. Classes novas no module.css: `.toggleRow`, `.toggleBtn`.
- **Endpoints:** `GET /api/v1/settings` (campos nulos se nunca salvos), `PUT /api/v1/settings` (parcial — só os campos enviados mudam; `null` limpa; string vazia → `None`; `extra="forbid"`; `preco ge=0`), `POST /api/v1/messages/reply` → `{ mensagens: [{autor: "cliente"|"vendedor", texto}] }` → `{ raciocinio, mensagem }` — a **última** mensagem deve ser do cliente (400 senão; 422 se a lista for vazia). Aceita payload extra `{ lead_id?: int }`. **Histórico (v0.3.5):** `GET /api/v1/messages/lead/{id}` → lista `{ autor, texto, raciocinio? }` em ordem de troca, `POST /api/v1/messages` → salva uma mensagem avulsa (`autor`, `texto`, `lead_id?`, `raciocinio?`; 201) e `DELETE /api/v1/messages/lead/{id}` → apaga a conversa do lead (204, o "Nova conversa"). Nos **três** o lead é validado pelo `LeadRepository` escopado: inexistente/alheio → **404** (não vaza existência); sem token → 401. **Lista de conversas (v0.3.6):** `GET /api/v1/messages/conversations` → `[ConversationSummary]` — uma linha por lead **com** histórico (`lead_id`, `nome`, `empresa`, `instagram`, `produto`, `status`, `total` de mensagens, `ultima_em`), da atividade mais recente para a mais antiga; agrupada no `MessageRepository.conversations()` (join com `Lead` escopado — lead apagado some da lista) e sem lead → lista vazia.
- **Dados:** tabela `user_settings` (linha única por `user_id`, `preco Numeric(10,2)` NULL = não configurado) + tabela `messages` (`user_id` FK + `lead_id` FK, `autor` "cliente"/"vendedor", `texto`, `raciocinio`, `criado_em` com `server_default=now()`) — as duas criadas pelo `create_all` do lifespan. `create_all` **não altera tabela existente** → `_ensure_message_raciocinio_column()` no lifespan faz `ALTER TABLE messages ADD COLUMN IF NOT EXISTS raciocinio TEXT` (só Postgres; SQLite dos testes já nasce com a coluna).
- **Histórico por lead PERSISTIDO (v0.3.5):** `MessageService.reply()` grava a **fala do cliente + a sugestão gerada** (com `raciocinio`) num **único commit** quando há `lead_id` — é o que faz a conversa reaparecer ao reabrir o lead; sem `lead_id` nada é gravado (o chat avulso continua só no estado da página). A persistência é **melhor-esforço**: exceção de banco vira log `reply_history_persist_failed` e a resposta já validada ainda é entregue (testado). `MessageRepository.create()` é **idempotente por lead** (última mensagem com mesmo autor+texto → devolve a existente): cobre o duplo-run de efeito do React StrictMode e duplo clique na abertura. Ordenação por **`id`** (não `criado_em` — precisão de segundo daria empate instável). Falha de persistência nunca derruba o `reply`.
- **Config/limites:** reusa `OPENROUTER_API_KEY`/`AI_CHAT_MODEL` e o `get_http_client()` compartilhado; `REPLY_TIMEOUT_SECONDS=60`; `rate_limit_user` (100 req/min) no `APIRouter` de `/messages` (reply + histórico) e em `/excavate`; sem chave → 502 `OPENROUTER_API_KEY não configurada no .env`.
- **Frontend:** `settingsApi` em `client.ts` + `generateReply()` em `api/messages.ts`; histórico em `client.ts` (`loadConversation` / `saveMessage` / `clearConversation` — `StoredMessage` carrega `raciocinio` para o card voltar completo) + `listConversations`/`ConversationSummary` (painel Leads); `Sidebar` ganhou o item **Abordagem**; ao falhar a geração o texto volta para o campo (o histórico não fica com mensagem sem resposta).
- **Frontend — ciclo de vida do histórico:** ao abrir `/abordagem?lead=<id>` a página carrega o histórico (`historyLoaded`) **antes** de criar a abertura automática — espera `lead && settingsLoaded && historyLoaded && entries.length === 0`, então nunca sobrescreve conversa salva; entradas recebidas ganham ids únicos de `nextId.current++` (sem `id: 0` duplicado nas keys) e falha de leitura é engolida (conversa começa do zero). O **envio** não salva mais nada na tela: o backend persiste no `reply`. A **abertura** (etapa 1) é salva via `saveMessage` (fire-and-forget) e o **"Nova conversa"** chama `DELETE /lead/{id}` antes de recriar a abertura — sem isso a conversa antiga voltaria no reload. Sem lead, nada é persistido.
- **Frontend — switch Config/Leads (v0.3.6):** a coluna esquerda da `/abordagem` virou um switch de dois botões (`leftPanel: "config" | "leads"`, com `aria-pressed` — o antigo toggle "Mostrar/Ocultar config" saiu). No painel **Leads**, `GET /messages/conversations` recarrega **a cada abertura** do painel e renderiza a lista (`leadList`/`leadItem` com nome, meta instagram/empresa + produto + total de mensagens; o item ativo usa `leadItemActive` + `aria-current`). Clicar num item chama `openLead(id)` → `setLeadId(id)` + `router.replace('/abordagem?lead=<id>')`. O lead passou a viver no **estado `leadId`** (e não mais lido só na montagem): um efeito `[leadId]` reseta chat/histórico e recarrega ficha + conversa (tudo com flag `cancelled`, então trocas rápidas não misturam respostas). `clearLead` faz `setLeadId(null)` e limpa a URL.
- **Testes:** `test_settings.py` (10) + `test_messages.py` (**49** = 16 originais + 8 do `TestLeadContext` + 3 do retry/fallback v0.3.4 + 15 do `TestConversationHistory` v0.3.5 + 7 do `TestConversationsList` v0.3.6) — `MessageService._chat` é monkeypatchado (nenhum teste depende de rede/chave) e cobre papéis do transcript, formato pt-BR do preço (`R$ 1.200,50`), o guardrail (preço errado, parcelamento 3x, valor sem preço configurado, violação no raciocínio, JSON inválido), o contexto de lead, o retry de formato, o histórico (persistência do `reply`, ordem, isolamento por usuário, 404 de lead alheio, idempotência do save, `DELETE` e falha de banco não derruba o `reply`) e a lista de conversas (lead sem histórico fora, ordenação por atividade, mensagens avulsas sem lead não contam, isolamento por usuário e apagar lead com histórico não quebra — FK sem CASCADE). Total backend: **233 testes passando** (~20s).
- **Watcher caveat:** rota nova `/abordagem` só aparece após `docker compose restart frontend` — o `next dev` dentro do container Windows→Docker não re-escaneia bind mounts novos. Adicione `WATCHPACK_POLLING=true` ao `frontend` service no `docker-compose.yml` para evitar o problema em desenvolvimentos futuros.

### 3.11 Normalização de enumeração de produto/dificuldade

| Campo | Valor do Prompt (o que a IA volta) | Valor real do enum (banco) | Normalização |
|-------|-----------------------------------|---------------------------|-------------|
| `produto` | `"página de venda"` / `"link tree"` | `"Página de vendas"` / `"Link Tree"` | `_normalize_produto()` no backend: minúsculo/sem acento → canonical; desconhecido → `"Portfólio"` |
| `dificuldade` | `"facil"` / `"media"` / `"dificil"` | `"Fácil"` / `"Médio"` / `"Difícil"` | `_normalize_dificuldade()` no backend: mesmo processo; desconhecido → `"Médio"` |
| Frontend | `toProduto()` / `toDificuldade()` em `excavator.ts` — espelha o backend para cards já excavados antes da correção |

Essa normalização evita o erro 422 `{"field":"produto","type":"enum","message":"valor não permitido"}` ao criar lead via `POST /api/v1/leads` e cobre cards excavados anteriormente que ainda guardam o valor antigo no estado da página.

---

---

## 4. Convenções de Código (Skills `.agents/`)

### 4.1 CSS e Componentização (SKILL_CSS.md)

- **Nunca** CSS inline (`style={{ ... }}`) para propriedades estáticas.
- Todo componente `Foo.tsx` tem `Foo.module.css` correspondente.
- Tokens de tema (cores, espaçamento, tipografia) vivem em `src/styles/tokens.css`.
- Componentizar quando: repetição ≥2x, componente >150–200 linhas, estado isolado ou reuso real.
- **Textos visíveis (v0.3.7):** nenhum travessão "—" em frase da UI — usar ponto ou vírgula no lugar. Exceções: o placeholder de célula vazia da tabela de Leads (`"—"`) e os separadores `──`/comentários de código (não são texto visível).

### 4.2 Qualidade e Testes (SKILL_Qualidade_e_Padroes.md)

- **Biome** para lint + format no frontend (substitui ESLint + Prettier).
- **TDD obrigatório** para backend FastAPI e lógica de negócio frontend.
- **TDD recomendado** para componentes UI em iteração de design.
- Todo endpoint valida payload com schema Pydantic.
- Nunca SQL por concatenação — sempre ORM (SQLAlchemy) ou query parametrizada.
- Cobertura mínima sugerida: 70% em lógica de negócio backend.

### 4.3 Segurança e LGPD (SKILL_Seguranca_e_LGPD.md)

- Secrets **sempre** em `.env` (gitignored), nunca hardcoded.
- Logs em JSON estruturado (structlog), com `request_id` por request.
- Redação de PII em logs: e-mail, CPF, token, senha → `[REDACTED_*]`.
- Erros em `application/problem+json` (RFC 7807), sem stack trace para o cliente.
- Stack trace completo apenas em log interno.
- Validação Pydantic em todo endpoint — rejeitar campos fora do schema.
- Rate limit em endpoints públicos — ✅ implementado (auth por IP + cota por usuário, ver §3.9).

---

## 5. Arquitetura em Camadas (Backend)

```
Router  →  Service  →  Repository  →  Database
(só HTTP)  (regra de negócio)  (SQL/ORM)
```

| Camada | Responsabilidade | Pode importar |
|--------|-----------------|---------------|
| `routes/` | Receber input, chamar service, retornar schema | services, schemas, exceptions |
| `services/` | Validações de negócio, orquestração | repositories, schemas, exceptions |
| `repositories/` | Queries SQLAlchemy, acesso a dados | models |
| `models/` | Definição de tabelas | database |
| `schemas/` | Validação Pydantic (request/response) | — |

**Regra:** `routes/` nunca contém SQL, regra de negócio ou chamada direta a repository.

---

## 6. Stack Técnico Detalhado

### 6.1 Backend (FastAPI)

| Pacote | Versão | Uso |
|--------|--------|-----|
| fastapi | 0.115.6 | Framework HTTP |
| sqlalchemy | 2.0.36 | ORM |
| psycopg2-binary | 2.9.10 | Driver PostgreSQL |
| apify-client | 1.8.1 | Scraping Instagram (Escavador) |
| apify-shared | >=1.1.2,<2 | **Pin obrigatório** — a 2.x removeu `ignore_docs` e quebrava o import do apify-client (todo `/excavate` → 502) |
| pydantic-settings | 2.7.0 | Config via env vars |
| python-jose[cryptography] | 3.3.0 | JWT (encode/decode HS256) |
| passlib[bcrypt] | 1.7.4 | Hash de senha (bcrypt) |
| bcrypt | 4.0.1 | PINADO — passlib 1.7.4 quebra com ≥4.1 |
| python-multipart | 0.0.20 | Form data (requisito FastAPI) |
| structlog | 24.4.0 | Logging JSON estruturado |
| sentry-sdk | 2.19.0 | Error tracking (destino de observabilidade) |
| opentelemetry-api/sdk | 1.29.0 | Instrumentação vendor-neutral |
| pytest + httpx | — | Testes |

**Padrão de config:** `pydantic-settings` com `extra = "forbid"`. Nenhum secret hardcoded.

### 6.2 Frontend (Next.js)

| Pacote | Versão | Uso |
|--------|--------|-----|
| next | 15.1.3 | Framework React (App Router) |
| react | 19.0.0 | UI library |
| @biomejs/biome | 1.9.4 | Lint + format |
| openapi-typescript | 7.4.4 | Gera types TS do OpenAPI |

### 6.3 Banco de Dados

| Item | Valor |
|------|-------|
| Engine | PostgreSQL 16 (alpine) |
| Container | `syslink_db` |
| Volume | `pgdata` (persistente) |
| Healthcheck | `pg_isready` a cada 5s |

---

## 7. Segredos e Variáveis de Ambiente

Todas as chaves vivem no `.env` na raiz (nunca commitado).

| Variável | Uso | Onde é lida |
|----------|-----|-------------|
| `DB_USER` | Usuário PostgreSQL | docker-compose, backend |
| `DB_PASSWORD` | Senha PostgreSQL | docker-compose, backend |
| `DB_NAME` | Nome do banco | docker-compose, backend |
| `DB_PORT` | Porta exposta do banco | docker-compose |
| `SECRET_KEY` | Segredo da aplicação (JWT, etc.) | backend |
| `ENVIRONMENT` | `development` / `production` | backend |
| `LOG_LEVEL` | `DEBUG` / `INFO` / `WARNING` / `ERROR` | backend |
| `SENTRY_DSN` | DSN do Sentry (opcional) | backend |
| `OPENROUTER_API_KEY` | Chave da OpenRouter para IA | backend |
| `AI_MODEL` | Modelo de embeddings Nemotron | backend |
| `AI_CHAT_MODEL` | Modelo de chat para classificação | backend |
| `APIFY_API_TOKEN` | Chave da Apify para scraping Instagram | backend |
| `APIFY_ACTOR_ID` | Actor do Apify (default: instagram-search-scraper) | backend |
| `TAVILY_API_KEY` | Chave da Tavily (busca Instagram em paralelo à Apify; vazia = só Apify) | backend |
| `RESEND_API_KEY` | Chave da API Resend (envio de e-mails) | backend |
| `RESEND_FROM` | Remetente dos e-mails (ex.: `SysLink <no-reply@dom.com>`) | backend |
| `FRONTEND_URL` | Base dos links nos e-mails (default `http://localhost:3000`) | backend |
| `RATE_LIMIT_AUTH_PER_MINUTE` | Req/min por IP na auth pública (default 5; 0 = off) | backend |
| `RATE_LIMIT_USER_PER_MINUTE` | Req/min por user_id nas rotas autenticadas (default 100; 0 = off) | backend |
| `EXCAVATE_DAILY_PROFILE_LIMIT` | Perfis escavados por usuário por dia BRT (default 50; 0 = cota desativada) | backend |
| `TRUST_PROXY_HEADERS` | `true` só atrás de proxy confiável — lê `X-Forwarded-For` (default `false`) | backend |
| `FRONTEND_PORT` | Porta do Next.js | docker-compose |
| `BACKEND_PORT` | Porta do FastAPI | docker-compose |

**Regras:**
- `.env.example` sempre atualizado com placeholders.
- `.env` no `.gitignore` — nunca commitar.
- Em produção: AWS Secrets Manager (não arquivos).

---

## 8. Docker Compose

Um único `docker-compose.yml` na raiz com três serviços:

| Serviço | Container | Porta | Dependência |
|---------|-----------|-------|-------------|
| `db` | syslink_db | 5432 | — |
| `backend` | syslink_backend | 8000 | db (healthy) |
| `frontend` | syslink_frontend | 3000 | backend |

- `db` tem healthcheck (`pg_isready`).
- `backend` depende do `db` com `condition: service_healthy`.
- Volumes de desenvolvimento: código montado com `--reload` / `npm run dev`.

---

## 9. Observabilidade

- **Instrumentação:** OpenTelemetry (vendor-neutral) em todo backend.
- **Destino padrão:** Sentry (error tracking + traces).
- **Logging:** structlog JSON com campos `timestamp`, `level`, `message`, `request_id`.
- **Request ID:** gerado por `RequestIDMiddleware`, propagado em headers `x-request-id`.
- **Erro para cliente:** `application/problem+json` (RFC 7807), sem stack trace.
- **Erro em log:** stack trace completo (só interno).

---

## 10. LGPD — Pendências

- [ ] Consentimento explícito documentado (`consent_id`).
- [ ] Endpoint `DELETE /users/{id}/data` (direito ao esquecimento).
- [ ] Soft delete (`deleted_at`) + anonimização de PII.
- [ ] Política de retenção (ex: 90 dias → purga).
- [ ] Auditoria de acesso a dados sensíveis (`audit_logs`).
- [ ] Termos de privacidade versionados.

---

## 11. Próximos Passos

- [ ] Alembic para migrations (substituir `create_all` do lifespan).
- [ ] Preencher `RESEND_API_KEY`/`RESEND_FROM` no `.env` e validar o envio real dos e-mails de confirmação/recuperação.
- [ ] Configurar CI (GitHub Actions): lint Biome + pytest + cobertura.
- [ ] Integrar Sentry (DSN via env).
- [ ] Rodar `npm run api:sync` para gerar types TypeScript do OpenAPI.
- [ ] Dependabot / Renovate para atualização de dependências.

---

*Atualizar este arquivo sempre que houver mudança de stack, convenção ou arquitetura.*
