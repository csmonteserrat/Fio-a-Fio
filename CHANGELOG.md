# Histórico de versões

## 1.0.0 · 2026-10-08

Primeira versão completa, construída e testada como artefato no Claude e migrada para site.

**Coleta**
- Questionários Q1 (pacientes), Q2 (ACS) e Q3 (equipe), com aplicação na tela etapa por etapa e digitação de papel.
- Pergunta 4 com a mesma lista de 41 temas nos três grupos, incluindo o grupo Saúde bucal; ACS e equipe marcam até 2 por grupo e os 3 mais urgentes.
- Q2 e Q3 com a lista nominal da equipe do CS Monte Serrat, controle de quem já respondeu e opção de não se identificar; no Q3, nome livre para quem não está na lista.
- Q3 por link online: link pessoal (uso único) ou geral.
- Entrada como avaliador (só aplica questionários) ou administrador (acesso a tudo). O administrador entra só com o nome de usuário; o `@fioafio.app` é completado pelo site.

**Análise**
- Panorama com temas convergentes, comparação das três escutas e metas de resposta (50 pacientes, 9 ACS, 31 profissionais).
- Estatística em Python: IC de Wilson, Spearman, W de Kendall, Fisher e qui-quadrado com Benjamini-Hochberg, Kruskal-Wallis, matriz com IC t; resultados com p < 0,05 em negrito.
- Análise de conteúdo temática: codificação com sugestões do Claude, livro de códigos, triangulação, saturação, kappa de Cohen entre codificadores, consenso e fichas de temas geradores.
- Tutorial de leitura e interpretação de cada resultado.
- Script de publicação que reproduz todas as tabelas a partir de uma exportação anonimizada.

**Infraestrutura**
- Supabase (dados, login e regras de acesso), API FastAPI no Render, site estático no Render.
