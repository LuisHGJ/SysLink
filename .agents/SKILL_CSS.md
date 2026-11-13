---
name: frontend-code-standard
description: Padrão de organização de estilos (CSS) e componentização para o frontend React da empresa. Use sempre que for criar ou revisar qualquer componente React — define que CSS nunca é inline, que propriedades visuais globais (cores de tema, cor de botão, espaçamento base) vão em um arquivo de estilização global, e quando extrair um componente novo. Use também quando o usuário perguntar "isso deveria ser um componente separado?" ou "onde eu coloco esse estilo?".
---

# Padrão de CSS e componentização — Frontend React

## 1. Nunca usar CSS inline

- Proibido `style={{ ... }}` no JSX para estilização de layout/aparência, exceto para valores realmente dinâmicos calculados em runtime que não podem existir como classe (ex.: posição de um elemento arrastável, largura vinda de uma medição de DOM). Cor, espaçamento, tipografia e borda **nunca** são inline, mesmo que pareça "só uma linha".
- Todo componente `Foo.tsx` tem seu arquivo de estilo correspondente (`Foo.module.css`, ou o padrão de CSS-in-JS já adotado no projeto — mas sempre em arquivo separado, nunca atributo `style`).
- Motivo: CSS inline não é cacheável, não participa do lint/format do Biome, e quebra a possibilidade de sobrescrever por tema (claro/escuro).

## 2. Arquivo de estilização global para propriedades gerais

Qualquer propriedade visual que **não é específica de um componente** — ou seja, é reutilizada ou representa uma decisão de tema — vai em um arquivo global (`theme.css` / `tokens.css` ou equivalente do design system do projeto), nunca redefinida solta dentro do CSS de um componente.

Exemplos do que é "geral" e vai pro arquivo global:
- Cores de tema claro/escuro (`--color-bg`, `--color-text`, `--color-primary`).
- Cor e estado de botões (`--button-bg`, `--button-bg-hover`, `--button-disabled`).
- Escala de espaçamento (`--spacing-sm`, `--spacing-md`, ...).
- Tipografia base (família, tamanhos da escala, pesos).
- Raio de borda padrão, sombras padrão.

Regra prática: se ao mudar esse valor você esperaria que **mais de um componente** mudasse junto, ele é global. Se o valor só faz sentido para aquele componente específico, fica no CSS local dele.

## 3. Componentização sempre que necessário

"Sempre que necessário" não é "sempre" — componentizar sem critério gera indireção desnecessária. Extraia um componente novo quando pelo menos um destes for verdadeiro:

- O mesmo trecho de JSX se repete em **2 ou mais lugares** — nesse ponto, extrair evita duplicação e desalinhamento futuro.
- O componente atual passou de ~150–200 linhas ou está misturando responsabilidades diferentes (ex.: lógica de fetch + layout + formulário no mesmo arquivo).
- Um pedaço da UI tem estado ou lógica isolada que pode ser testada/entendida separadamente do resto (ex.: um card de item de lista, um seletor de data).
- O componente será reutilizado em outra tela, mesmo que hoje só exista em uma.

Não componentize preventivamente "porque pode ser reutilizado um dia" sem nenhum dos sinais acima — isso é o oposto do problema de CSS inline: indireção sem necessidade real, difícil de navegar depois.

## Checklist de PR (frontend)

- [ ] Nenhum `style={{ ... }}` novo para propriedades estáticas (cor, espaçamento, tipografia, borda).
- [ ] Toda cor/espaçamento/tipografia de tema referencia uma variável do arquivo global, não um valor hardcoded local.
- [ ] Componentes extraídos têm justificativa clara (repetição, tamanho, responsabilidade isolada ou reuso) — não extração especulativa.
