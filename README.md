# Fio a Fio · Levantamento participativo de temas

**Versão 1.0** (`VERSION` = 1.0.0) · Centro de Saúde Monte Serrat, Florianópolis (SC)

Painel para aplicar, digitar e analisar os questionários do Projeto Fio a Fio, que escolhe com a comunidade, os agentes comunitários e a equipe os temas dos vídeos de educação em saúde da sala de espera.

- **Q1** pacientes e comunidade (amostra; meta mínima de 50)
- **Q2** agentes comunitários de saúde (censo; 9 ACS)
- **Q3** equipe de saúde (censo; 31 profissionais), também por link online

## Onde estamos nos deploys

| Versão | Data | Onde roda | O que mudou |
|---|---|---|---|
| **1.0** | 2026-10-08 | Artefato de testes no Claude e este repositório (site ainda não publicado) | Primeira versão completa. Veja o [CHANGELOG](CHANGELOG.md). |

A versão aparece no menu lateral do site, na tela de entrada e em `GET /api/saude`. Ao publicar uma versão nova, atualize nesta ordem: `VERSION`, `FIO_VERSAO` no `web/index.html`, `versao` em `analise/instrumento.json`, o `CHANGELOG.md`, esta tabela, e crie a tag no git (`git tag v1.1.0`). O teste `tests/test_api.py` acusa se a versão do site e a do arquivo `VERSION` divergirem.

## Arquitetura

```
 Navegador (web/)                    Render                         Supabase
 ┌──────────────────────┐   login   ┌──────────────────────┐       ┌───────────────────────┐
 │ index.html (painel)  │──────────▶│                      │       │ Auth (contas)         │
 │ adapter.js           │◀─ dados ─▶│                      │◀─────▶│ Postgres + RLS        │
 │ config.js            │           │ API Python (api/)    │ token │ funções do link Q3    │
 └─────────┬────────────┘           │ FastAPI + analise/   │       └───────────────────────┘
           │ registros  ──────────▶ │ estatística e        │
           │ resultados ◀────────── │ métricas temáticas   │──▶ API do Claude (sugestões)
           └────────────────────────┴──────────────────────┘
```

- **Supabase** guarda os dados e cuida do login. As regras de acesso (RLS) ficam no banco: avaliador lê e inclui respostas; só administrador edita, exclui e acessa a análise temática; quem recebe o link do Q3 só consegue responder, sem ler nada.
- **API Python** é uma calculadora: recebe os registros que o painel já leu e devolve as análises. Os cálculos estatísticos e as métricas qualitativas são feitos **só em Python**, no pacote `analise/`, o mesmo usado no script da publicação.
- **Site estático** é o painel. O panorama (triagem visual) é calculado no navegador; estatística, triangulação, saturação e concordância vêm da API.

## Estrutura

```
analise/            pacote Python: instrumento, estatística, qualitativa, dados
  instrumento.json  fonte única das listas de temas, opções e equipe
api/main.py         API FastAPI
web/                site estático (index.html, adapter.js, build.sh, config.example.js)
supabase/schema.sql tabelas, regras de acesso e funções do link online
publicacao/         script que reproduz todas as tabelas do artigo
scripts/            importação dos dados do painel de testes
tests/              testes (referências SciPy, paridade com o painel, API, versão)
render.yaml         deploy no Render (Blueprint)
```

## Como publicar

### 1. Supabase

1. Crie um projeto em [supabase.com](https://supabase.com), na região **South America (São Paulo)**.
2. Em **SQL Editor**, cole e rode `supabase/schema.sql`.
3. Em **Authentication > Users > Add user**, crie, marcando *Auto Confirm User*:
   - a sua conta de administrador (e as de outros administradores, se houver);
   - a conta única dos avaliadores, `avaliador@fioafio.app` (o e-mail pode ser fictício).
4. Dê o papel de cada conta rodando o bloco comentado no fim do `schema.sql`, trocando os e-mails.
5. Em **Project Settings > API**, copie a *Project URL* e a chave *anon public*. A chave *service_role* nunca vai para o site.

### 2. GitHub

Suba esta pasta para um repositório. Pode ser público: não há dados nem segredos no código (`.gitignore` bloqueia `dados/`, `*.csv`, `.env` e `web/config.js`).

### 3. Render

1. **New > Blueprint**, escolha o repositório. O `render.yaml` cria dois serviços: `fioafio-api` (Python) e `fioafio-site` (estático).
2. Preencha as variáveis:
   - API: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `WEB_ORIGIN` (endereço do site, ex. `https://fioafio-site.onrender.com`) e, para as sugestões do Claude, `ANTHROPIC_API_KEY`.
   - Site: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `API_URL` (endereço da API, ex. `https://fioafio-api.onrender.com`).
3. Abra o site, entre como administrador e confira a página Estatística.

No plano gratuito, a API "dorme" sem uso e a primeira análise do dia pode levar até 1 minuto.

### 4. Trazer os dados do painel de testes (opcional)

Exporte os dados do artefato para JSON e rode `python scripts/importar_artefato.py arquivo.json` com o `.env` preenchido.

## Desenvolvimento local

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
pytest                                    # 21 testes
FIO_DEV_SEM_AUTH=1 uvicorn api.main:app --reload --port 8765
cp web/config.example.js web/config.js    # aponte API_URL para http://127.0.0.1:8765
python -m http.server 8000 -d web
```

## Análise para a publicação

```bash
python -m analise.dados exportar          # lê o Supabase com a chave service_role do .env e anonimiza
python publicacao/analise_publicacao.py dados/fioafio_anonimizado.json
```

Gera em `saida/` as tabelas (temas com IC 95%, concordância, perfil com q de Benjamini-Hochberg, matriz da equipe, proporções), as métricas temáticas, o texto de métodos e as versões das bibliotecas.

- **Métodos:** IC de Wilson; Spearman e W de Kendall; Fisher e qui-quadrado com correção de Benjamini-Hochberg; Kruskal-Wallis; média com IC pela distribuição t; kappa de Cohen (Landis e Koch). Detalhes nas docstrings de `analise/estatistica.py` e `analise/qualitativa.py`.
- **Reprodutibilidade:** bibliotecas com versão fixa em `requirements.txt`. Para citar o código, crie um release no GitHub e arquive no [Zenodo](https://zenodo.org) para obter um DOI.
- **Dados:** ficam no Supabase. Só uma cópia anonimizada sai de lá, e só se o CEP e o termo de consentimento permitirem divulgá-la. Revise as respostas abertas antes: elas podem conter nomes.

## Segurança, ética e LGPD

- Login individual para administradores e conta única para avaliadores, com o nome de quem aplica registrado em cada questionário.
- As regras de acesso estão no banco (RLS), testadas em `supabase/schema.sql` com um Postgres local.
- A chave *service_role* só é usada no seu computador, para exportar dados. A chave da API do Claude fica só no servidor.
- Os questionários de pacientes são anônimos. Q2 e Q3 registram o nome (com opção de não se identificar) para controlar o censo; os nomes não aparecem nas análises.
- Antes de coletar para publicação: aprovação no CEP (Resoluções CNS 466/2012 e 510/2016) e termo de consentimento.

## Limitações conhecidas da versão 1.0

- A senha da conta dos avaliadores é trocada no painel do Supabase, não no site.
- No link geral do Q3, a lista de nomes não mostra quem já respondeu; o banco recusa a segunda resposta da mesma pessoa.
- As definições do instrumento existem em `analise/instrumento.json` e no `web/index.html`; o teste `test_instrumento_igual_ao_site` garante que estejam iguais.
