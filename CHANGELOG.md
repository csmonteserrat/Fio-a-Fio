# Histórico de versões

## 1.4.0 · 2026-10-08

**Coleta**
- Q1: botão **Não** nas perguntas 6 e 12 e botão **Nenhuma** na pergunta 7, com o mesmo comportamento dos botões da 1.3 (limpa e trava o campo, conta como respondida, aparece no CSV).

## 1.3.0 · 2026-10-08

**Coleta**
- Q1: textos de todas as perguntas reescritos em linguagem de conversa (idade, gênero, tempo de moradia, dúvidas, "fofoca do portão", barreiras, TV, tipo de vídeo, pedido de vídeo, repasse e sugestões), com exemplos nas perguntas 6, 7 e 12. Os nomes curtos antigos continuam nas colunas do CSV e na análise.
- Q1, pergunta 5: botão **Não** (a pessoa não tem outro tema). Q1, pergunta 10: botão **Nenhum** (a pessoa não quer pedir vídeo). Marcar o botão limpa e trava o campo, conta como pergunta respondida e aparece no CSV como "Não" ou "Nenhum".

## 1.2.0 · 2026-10-08

**Coleta**
- Q3, pergunta 7 (matriz): cada tema ganhou um botão × para cortar o tema quando ele não faz parte da prática da pessoa, quando ela prefere não avaliar ou quando não sabe responder. O tema cortado sai do cálculo daquele tema e não conta como nota baixa; fica registrado como `na` (e como `n/a` no CSV).
- Texto de orientação acima da matriz: o que significa cada escala, quando usar o ×, e o pedido para usar a escala toda e não dar 5 (ou 1) para todos os temas.
- Notas coloridas: na frequência na demanda, verde no 1 até vermelho no 5; no potencial educativo, vermelho no 1 até verde no 5. O número continua escrito em cada botão.

**Análise**
- A matriz da equipe mostra quantos profissionais cortaram cada tema (coluna Fora da prática) e `fora_da_pratica` na tabela da publicação; o texto de métodos descreve a regra de exclusão. Novo teste cobre o cálculo.

**Segurança dos dados**
- Restaurar backup pelo site (página Acesso, administrador): escolhe o arquivo, mostra o que há nele e o que há hoje no site, pede confirmação e, por padrão, baixa antes um backup do estado atual. A restauração acrescenta e atualiza por identificador e nunca apaga.

## 1.1.0 · 2026-10-08

**Coleta**
- O administrador entra só com o nome de usuário; o `@fioafio.app` é completado pelo site.
- O avaliador digita o próprio nome (sem lista de escolha).
- Questionário em branco não é salvo; cada questionário da lista mostra a porcentagem preenchida (e a coluna `% preenchido` no CSV).
- Q3, pergunta 5 (lista de temas): obrigatório marcar as 3 urgências (estrelas) no total da lista; não é preciso escolher temas em todos os grupos.
- Textos revisados no Q2 (perguntas 10, 13 e 14) e no Q3 (perguntas 3 e 6 a 14).
- Q3: a pergunta sobre o abismo técnico-popular passou a ser a 4, logo depois dos três problemas, e a lista de temas virou a 5. A pergunta 4 mostra como botões os problemas digitados na 3 e abre um campo de texto para cada um (o texto é guardado em `q4`, com o detalhe por problema em `q4d`). A matriz passou a se chamar frequência na demanda × potencial educativo.

**Segurança dos dados**
- Botão Baixar backup na página Acesso (administrador): baixa um JSON com todas as coleções, restaurável com `scripts/importar_artefato.py`; mostra a data do último backup baixado no navegador.

**Documentação**
- README com o passo a passo do Render, das chaves do Supabase e do backup.

## 1.0.0 · 2026-10-08

Primeira versão completa, construída e testada como artefato no Claude e migrada para site.

**Coleta**
- Questionários Q1 (pacientes), Q2 (ACS) e Q3 (equipe), com aplicação na tela etapa por etapa e digitação de papel.
- Pergunta 4 com a mesma lista de 41 temas nos três grupos, incluindo o grupo Saúde bucal; ACS e equipe marcam até 2 por grupo e os 3 mais urgentes.
- Q2 e Q3 com a lista nominal da equipe do CS Monte Serrat, controle de quem já respondeu e opção de não se identificar; no Q3, nome livre para quem não está na lista.
- Q3 por link online: link pessoal (uso único) ou geral.
- Entrada como avaliador (só aplica questionários) ou administrador (acesso a tudo).

**Análise**
- Panorama com temas convergentes, comparação das três escutas e metas de resposta (50 pacientes, 9 ACS, 31 profissionais).
- Estatística em Python: IC de Wilson, Spearman, W de Kendall, Fisher e qui-quadrado com Benjamini-Hochberg, Kruskal-Wallis, matriz com IC t; resultados com p < 0,05 em negrito.
- Análise de conteúdo temática: codificação com sugestões do Claude, livro de códigos, triangulação, saturação, kappa de Cohen entre codificadores, consenso e fichas de temas geradores.
- Tutorial de leitura e interpretação de cada resultado.
- Script de publicação que reproduz todas as tabelas a partir de uma exportação anonimizada.

**Infraestrutura**
- Supabase (dados, login e regras de acesso), API FastAPI no Render, site estático no Render.
