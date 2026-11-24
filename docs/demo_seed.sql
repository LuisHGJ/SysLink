-- Dados de demonstração para o README (usuário novo, aditivo)
BEGIN;

INSERT INTO users (email, password_hash, email_verified, created_at)
VALUES (
  'demo@syslink.dev',
  '$2b$12$z7h9eQuJv9Wo4d4QIUvReu5mPNbTp3S2aHYrXZcV1HEQeP6wcL/f6',
  true,
  now()
)
ON CONFLICT (email) DO NOTHING;

-- Configurações do vendedor (usadas pelo copiloto de Abordagem)
INSERT INTO user_settings (user_id, preco, nome_vendedor, empresa, tom_voz, atualizado_em)
SELECT id, 497.00, 'Luis Enrique', 'SysLink Studio',
       'Descomplicado, direto e um pouco informal. Sem jargão técnico exagerado.',
       now()
FROM users WHERE email = 'demo@syslink.dev'
ON CONFLICT (user_id) DO NOTHING;

-- Leads de exemplo (nicho: criadores de conteúdo e pequenos negócios)
INSERT INTO leads (nome, empresa, contato, instagram, produto, dificuldade, status,
                   motivo_perda, ultimo_contato, arquivos, user_id)
SELECT v.nome, v.empresa, v.contato, v.instagram, v.produto, v.dificuldade, v.status,
       v.motivo_perda, v.ultimo_contato, v.arquivos,
       (SELECT id FROM users WHERE email = 'demo@syslink.dev')
FROM (VALUES
  ('Marina Costa', 'Marina Fit', 'marina@marinafit.com.br', '@marina.fit', 'Link Tree', 'Fácil',
   'Negociando', NULL::text, '2026-11-21T14:30:00', '[]'::json),
  ('Rafael Duarte', 'Barbearia Duarte', '(11) 98812-4477', '@barbearia.duarte', 'Página de vendas', 'Médio',
   'Aguardando resposta', NULL::text, '2026-11-20T10:05:00', '[]'::json),
  ('Juliana Prado', 'Doces da Ju', NULL::varchar, '@docesdaju.sp', 'Link Tree', 'Fácil',
   'Não contatado', NULL::text, NULL::varchar, '[]'::json),
  ('Carlos Menezes', 'CM Engenharia', 'carlos@cmeng.com', '@cm.engenharia', 'Sistema', 'Difícil',
   'Fechado', NULL::text, '2026-11-18T16:45:00', '["proposta_v3.pdf"]'::json),
  ('Beatriz Lemos', 'Studio Bia alongamento', '@studio.bia', '@studio.bia', 'Portfólio', 'Fácil',
   'Finalizado', NULL::text, '2026-11-12T09:20:00', '[]'::json),
  ('Thiago Nunes', 'Nunes Music', '(21) 99771-2200', '@nunes.music', 'Página de vendas', 'Médio',
   'Negado', 'Orçamento acima do esperado dele', '2026-11-10T11:15:00', '[]'::json),
  ('Patrícia Alves', 'Paiva Clínica', 'contato@paivaclinica.com.br', '@paiva.clinica', 'Sistema', 'Difícil',
   'Em desenvolvimento', NULL::text, '2026-11-22T15:00:00', '["briefing.docx", "contrato.pdf"]'::json),
  ('Gustavo Reis', 'Reis Fotografia', NULL::varchar, '@gustavoreis.photo', 'Portfólio', 'Fácil',
   'Não contatado', NULL::text, NULL::varchar, '[]'::json),
  ('Amanda Rocha', 'Amanda Labels', 'amanda@labels.com', '@amanda.labels', 'Link Tree', 'Médio',
   'Aguardando resposta', NULL::text, '2026-11-23T08:40:00', '[]'::json),
  ('Diego Barros', 'Cross Barros', '(31) 98455-1122', '@crossbarros', 'Página de vendas', 'Difícil',
   'Não contatado', NULL::text, NULL::varchar, '[]'::json)
) AS v(nome, empresa, contato, instagram, produto, dificuldade, status, motivo_perda, ultimo_contato, arquivos)
WHERE NOT EXISTS (
  SELECT 1 FROM leads WHERE nome = v.nome AND user_id = (SELECT id FROM users WHERE email = 'demo@syslink.dev')
);

-- Conversa de exemplo com o copiloto (lead: Marina Costa)
INSERT INTO messages (user_id, lead_id, autor, texto, raciocinio, criado_em)
SELECT u.id, l.id, m.autor, m.texto, m.raciocinio, now() - (m.ago || ' minutes')::interval
FROM users u
JOIN leads l ON l.user_id = u.id AND l.nome = 'Marina Costa'
CROSS JOIN (VALUES
  ('cliente', 'Oi! Vi seu trabalho e fiquei interessada na página de links. Quanto custa?', NULL, 40),
  ('vendedor', 'Oi, Marina! Que bom que gostou. O investimento é de R$ 497, com página pronta em até 5 dias úteis e ajustes inclusos.', 'O cliente demonstrou interesse direto; respondi com preço à vista já configurado, sem abrir margem de negociação na primeira resposta.', 39),
  ('cliente', 'Fica um pouco acima do que eu tinha pensado... dá para parcelar?', NULL, 12),
  ('vendedor', 'Dá sim, Marina. Parcelo em até 6x de R$ 82,83 sem juros. Se preferir, fechamos hoje e eu começo o briefing ainda esta semana.', 'Ele pediu parcelamento, não recusou o valor. Ofereço a forma de pagamento que reduz a barreira e trago uma ação de fechamento com prazo.', 11)
) AS m(autor, texto, raciocinio, ago)
WHERE u.email = 'demo@syslink.dev'
  AND NOT EXISTS (SELECT 1 FROM messages WHERE lead_id = l.id);

COMMIT;
