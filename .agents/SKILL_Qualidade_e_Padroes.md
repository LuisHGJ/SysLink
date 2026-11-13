---
name: quality-observability-standard
description: Padrão de observabilidade, qualidade de código, testes e segurança de input para projetos React + FastAPI da empresa. Use ao configurar um novo projeto, ao revisar se um PR está pronto para merge, ou quando o usuário perguntar sobre monitoramento de erros, cobertura de testes, lint, qualidade de código, ou validação/sanitização de dados vindos do usuário. Também define a regra de que testes são escritos antes da funcionalidade (TDD) para lógica de negócio e backend, e que todo input do usuário é tratado como potencialmente malicioso.
---

# Padrão de qualidade, observabilidade e testes

## 1. Observabilidade — uma camada de instrumentação, um destino

Não instale Sentry, Datadog e New Relic ao mesmo tempo no mesmo serviço — é redundante (os três cobrem error tracking/APM) e triplica custo e manutenção.

- **Instrumentação**: OpenTelemetry (vendor-neutral) em todo serviço backend (FastAPI) e frontend crítico. Isso garante que trocar de destino no futuro não exige reinstrumentar o código.
- **Destino padrão**: Sentry (error tracking + traces) é suficiente para a maioria dos serviços React/FastAPI.
- Use Datadog ou New Relic **apenas** se a empresa já tiver contrato corporativo cobrindo esses serviços — não adicione por padrão.
- Todo erro não tratado (backend e frontend) deve chegar ao destino de observabilidade com stack trace e contexto de usuário/request (sem dados sensíveis/PII no payload).

## 2. Qualidade e lint de código

- **Biome**: lint + format único para todo o código JS/TS do frontend (substitui ESLint + Prettier separados).
- **Commitlint**: valida que toda mensagem de commit segue Conventional Commits (ver skill `github-workflow-standard`).
- **Knip**: detecta exports, dependências e arquivos não utilizados — rodar no CI, falhar o build se houver dead code novo.
- **Regra de arquitetura** (ex.: `dependency-cruiser` ou equivalente): define quais camadas podem importar quais (ex.: componente de UI não importa direto de camada de infraestrutura). Nomeie a ferramenta escolhida explicitamente no `package.json` do projeto — não deixe genérico.
- **Stryker**: mutation testing no backend/lógica crítica, para validar que os testes realmente pegam bugs (não só cobrem linhas). Rodar periodicamente (não a cada PR — é custoso), ex. semanal ou antes de releases maiores.

## 3. Testes — regra de TDD com escopo definido

**Backend (FastAPI) e lógica de negócio/estado (frontend): teste é escrito antes da implementação.** Isso é obrigatório, não sugestão — o teste define o contrato antes do código existir.

**Componentes de UI ainda em iteração de design/layout: TDD é recomendado, não obrigatório.** Layout muda muito durante o desenvolvimento inicial; exigir teste antes da funcionalidade nessa fase gera retrabalho de teste a cada ajuste visual. Assim que o componente estabiliza, cobertura de teste passa a ser obrigatória antes do merge (mesmo que não tenha sido escrita "antes").

- **Unitários**: toda função de lógica de negócio (backend) e todo hook/util com lógica não-trivial (frontend).
- **Integração**: toda rota de API (FastAPI) testada com banco/dependências reais ou containers de teste — não só mocks.
- **End-to-end**: Playwright cobrindo os fluxos críticos do usuário (login, ação principal do produto, fluxo de pagamento/checkout se houver). Não é necessário e2e para cada tela — só para os fluxos que, se quebrarem, geram impacto direto ao usuário.
- **Cobertura**: Codecov integrado ao CI, com limite mínimo definido por projeto (sugestão de partida: 70% em lógica de negócio backend, sem piso rígido em componentes visuais).

## 4. Segurança — nunca confiar em input do usuário

**Todo input vindo do usuário (formulário, query param, header, upload, payload de API) é tratado como potencialmente hostil por padrão** — trate cada campo como se o usuário estivesse tentando ativamente uma SQL injection, XSS ou payload malformado, mesmo que o campo pareça inofensivo (nome, e-mail, comentário).

- **Nunca montar SQL por concatenação de string.** Toda query usa ORM (SQLAlchemy) ou query parametrizada — sem exceção, mesmo em scripts internos.
- **Todo endpoint do FastAPI valida o payload com um schema Pydantic** — não aceitar `dict` solto ou campos não tipados. Rejeitar (400) qualquer campo fora do schema, não ignorar silenciosamente.
- **Sanitizar na saída, não só na entrada**: dado vindo do usuário que será renderizado no frontend é tratado como texto, não como HTML confiável (evita XSS) — React já escapa por padrão, mas cuidado redobrado com qualquer uso de `dangerouslySetInnerHTML`.
- **Limites explícitos**: tamanho máximo de string, tamanho máximo de upload, rate limit em endpoints públicos — nunca assumir que o cliente vai respeitar os limites da UI (o atacante não passa pelo formulário, passa direto pela API).
- Isso vale mesmo para campos preenchidos por usuários internos/autenticados — autenticação não é motivo para relaxar validação de input.

## 5. Checklist de PR

- [ ] Erros não tratados chegam ao Sentry (ou destino configurado) via OpenTelemetry.
- [ ] Lint (Biome) e regra de arquitetura passam sem exceções novas.
- [ ] Knip não aponta código morto introduzido pelo PR.
- [ ] Testes escritos antes da implementação para lógica de negócio/backend; testes presentes (mesmo que escritos depois) para UI estabilizada.
- [ ] Cobertura do Codecov não caiu em relação à branch principal.
- [ ] Todo endpoint novo/alterado valida input via Pydantic e usa query parametrizada/ORM — nenhuma concatenação de SQL.
