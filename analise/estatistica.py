"""Análise estatística dos questionários do Projeto Fio a Fio.

Todas as funções recebem os registros como dicionários, no mesmo formato em que
o site guarda as respostas (uma lista por questionário). Assim, o mesmo código
roda na API do site e no script de publicação.

Métodos (todos bilaterais, alfa = 0,05):
  * Proporções: intervalo de confiança de 95% de Wilson (Wilson, 1927).
  * Concordância entre grupos: correlação de postos de Spearman entre as
    proporções dos temas; W de Kendall com correção para empates.
  * Associação perfil x tema (Q1): teste exato de Fisher (tabelas 2x2) ou
    qui-quadrado de Pearson sem correção de continuidade (tabelas maiores);
    correção para comparações múltiplas de Benjamini e Hochberg (1995).
  * Número de temas por paciente entre faixas etárias: Kruskal-Wallis.
  * Matriz da equipe: média com IC 95% pela distribuição t e mediana.
"""
from __future__ import annotations

import math
from typing import Iterable, Sequence

import numpy as np
from scipy import stats
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.proportion import proportion_confint

from . import instrumento as I

ALFA = 0.05


# ---------------------------------------------------------------- utilitários
def _num(x):
    """Converte para float do Python, trocando NaN por None (JSON-friendly)."""
    if x is None:
        return None
    x = float(x)
    return None if math.isnan(x) or math.isinf(x) else x


def wilson(k: int, n: int) -> dict | None:
    """Proporção k/n com IC 95% de Wilson."""
    if not n:
        return None
    lo, hi = proportion_confint(k, n, alpha=ALFA, method="wilson")
    return {"k": int(k), "n": int(n), "p": k / n, "lo": float(lo), "hi": float(hi)}


def fisher(tab: Sequence[Sequence[int]]) -> float | None:
    """Teste exato de Fisher bilateral para tabela 2x2 [[a, b], [c, d]]."""
    (a, b), (c, d) = tab
    if a + b + c + d == 0:
        return None
    return _num(stats.fisher_exact([[a, b], [c, d]], alternative="two-sided")[1])


def qui_quadrado(tab: Sequence[Sequence[int]]) -> dict | None:
    """Qui-quadrado de Pearson (sem correção de Yates) para tabela r x c.

    Linhas e colunas vazias são removidas antes do teste. ``esperados_menor_5``
    é a fração de células com frequência esperada menor que 5.
    """
    t = np.asarray(tab, dtype=float)
    t = t[t.sum(axis=1) > 0]
    if t.shape[0] < 2:
        return None
    t = t[:, t.sum(axis=0) > 0]
    if t.shape[1] < 2:
        return None
    x, p, df, esp = stats.chi2_contingency(t, correction=False)
    return {"x": float(x), "df": int(df), "p": float(p), "esperados_menor_5": float((esp < 5).mean())}


def spearman(x: Sequence[float], y: Sequence[float]) -> dict | None:
    if len(x) < 4:
        return None
    r, p = stats.spearmanr(x, y)
    if r is None or (isinstance(r, float) and math.isnan(r)):
        return None
    return {"r": float(r), "p": _num(p), "n": len(x)}


def _postos_desc(v: Sequence[float]) -> tuple[np.ndarray, list[int]]:
    """Postos em ordem decrescente (1 = maior), com média nos empates."""
    arr = -np.asarray(v, dtype=float)
    r = stats.rankdata(arr, method="average")
    _, contagens = np.unique(arr, return_counts=True)
    return r, [int(c) for c in contagens if c > 1]


def kendall_w(colunas: Sequence[Sequence[float]]) -> dict | None:
    """W de Kendall para m avaliadores (grupos) e n itens (temas), com correção para empates."""
    m = len(colunas)
    if m < 2:
        return None
    n = len(colunas[0])
    if n < 3:
        return None
    R = np.zeros(n)
    T = 0.0
    for c in colunas:
        r, empates = _postos_desc(c)
        R += r
        T += sum(t**3 - t for t in empates)
    S = float(((R - R.mean()) ** 2).sum())
    W = 12 * S / (m * m * (n**3 - n) - m * T)
    x = m * (n - 1) * W
    return {"W": W, "m": m, "n": n, "x": x, "df": n - 1, "p": float(stats.chi2.sf(x, n - 1))}


def kruskal(grupos: Iterable[Sequence[float]]) -> dict | None:
    g = [list(a) for a in grupos if len(a)]
    if len(g) < 2 or sum(len(a) for a in g) < 5:
        return None
    try:
        H, p = stats.kruskal(*g)
    except ValueError:  # todos os valores iguais
        return None
    return {"H": float(H), "df": len(g) - 1, "p": float(p), "N": sum(len(a) for a in g)}


def benjamini_hochberg(ps: Sequence[float | None]) -> list[float | None]:
    idx = [i for i, p in enumerate(ps) if p is not None]
    q: list[float | None] = [None] * len(ps)
    if idx:
        corr = multipletests([ps[i] for i in idx], alpha=ALFA, method="fdr_bh")[1]
        for i, v in zip(idx, corr):
            q[i] = float(v)
    return q


def descritiva(valores: Iterable) -> dict | None:
    a = np.array([float(v) for v in valores if v is not None and not (isinstance(v, float) and math.isnan(v))])
    n = len(a)
    if not n:
        return None
    media = float(a.mean())
    dp = float(a.std(ddof=1)) if n > 1 else 0.0
    t = float(stats.t.ppf(0.975, n - 1)) if n > 1 else 0.0
    q1, med, q3 = (float(v) for v in np.percentile(a, [25, 50, 75]))
    return {"n": n, "media": media, "dp": dp, "mediana": med, "q1": q1, "q3": q3,
            "lo": media - t * dp / math.sqrt(n), "hi": media + t * dp / math.sqrt(n)}


def forca_rho(r: float) -> str:
    a = abs(r)
    return ("desprezível" if a < .1 else "fraca" if a < .3 else "moderada" if a < .5
            else "forte" if a < .7 else "muito forte")


def fmt_p(p: float | None) -> str:
    if p is None:
        return ""
    return "<0,001" if p < .001 else f"{p:.3f}".replace(".", ",")


# ---------------------------------------------------------------- análises
def _marcou(registro: dict, tema: str) -> bool:
    return tema in (registro.get("temas") or [])


def contagem_temas(registros: list[dict]) -> dict:
    n = len(registros)
    cnt = [sum(_marcou(r, t) for r in registros) for t in I.TEMA_IDS]
    urg = [sum(t in (r.get("temasU") or []) for r in registros) for t in I.TEMA_IDS]
    return {"n": n, "cnt": cnt, "urg": urg, "ic": [wilson(k, n) for k in cnt]}


def concordancia(grupos: dict[str, dict]) -> dict:
    """Spearman entre pares de grupos e W de Kendall entre todos os grupos com respostas."""
    disp = [q for q in ("q1", "q2", "q3") if grupos[q]["n"] > 0]
    prop = {q: [c / grupos[q]["n"] for c in grupos[q]["cnt"]] for q in disp}
    pares = []
    for i, a in enumerate(disp):
        for b in disp[i + 1:]:
            s = spearman(prop[a], prop[b]) or {}
            pares.append({"a": a, "b": b, **s})
    W = kendall_w([prop[q] for q in disp]) if len(disp) >= 2 else None
    postos = {q: _postos_desc(prop[q])[0].tolist() for q in disp}
    return {"grupos": disp, "pares": pares, "W": W, "postos": postos}


def perfil(q1: list[dict], variavel: str) -> dict:
    """Associação entre uma variável de perfil e cada tema da pergunta 4 (Q1)."""
    opcoes = I.VARIAVEIS_PERFIL[variavel]["opcoes"]
    n_opcao = [sum(r.get(variavel) == o for r in q1) for o in opcoes]
    linhas = []
    for t in I.TEMA_IDS:
        tab = []
        for o in opcoes:
            grp = [r for r in q1 if r.get(variavel) == o]
            k = sum(_marcou(r, t) for r in grp)
            tab.append([k, len(grp) - k])
        if variavel == "genero":
            p, teste, pequeno = fisher(tab), "Fisher", False
        else:
            c = qui_quadrado(tab)
            p = c["p"] if c else None
            pequeno = bool(c and c["esperados_menor_5"] > .2)
            teste = "χ² (esperados < 5)" if pequeno else "χ²"
        linhas.append({"tema": t, "tab": tab, "p": p, "teste": teste if p is not None else ""})
    qs = benjamini_hochberg([l["p"] for l in linhas])
    for l, q in zip(linhas, qs):
        l["q"] = q
    return {"variavel": variavel, "opcoes": opcoes, "n_opcao": n_opcao, "linhas": linhas}


def temas_por_pessoa(q1: list[dict]) -> dict:
    por = [len(r.get("temas") or []) for r in q1]
    por_idade = [[len(r.get("temas") or []) for r in q1 if r.get("idade") == o] for o in I.OPT["idade"]]
    return {"geral": descritiva(por), "faixas": I.OPT["idade"],
            "por_idade": [descritiva(v) for v in por_idade], "n_idade": [len(v) for v in por_idade],
            "kruskal": kruskal(por_idade)}


def matriz_equipe(q3: list[dict]) -> list[dict]:
    out = []
    for m in I.MX:
        f = descritiva(((r.get("mx") or {}).get(m["id"]) or {}).get("f") for r in q3)
        i = descritiva(((r.get("mx") or {}).get(m["id"]) or {}).get("i") for r in q3)
        out.append({"id": m["id"], "rotulo": m["label"], "f": f, "i": i,
                    "produto": (f["media"] * i["media"]) if f and i else None})
    return sorted(out, key=lambda x: -(x["produto"] or 0))


def _props(registros: list[dict], campo: str, opcoes: list[str], multipla=False, outra: str | None = None):
    n = len(registros)
    itens = []
    for o in opcoes:
        k = sum((o in (r.get(campo) or [])) if multipla else (r.get(campo) == o) for r in registros)
        itens.append({"rotulo": o, "k": k, **(wilson(k, n) or {})})
    if outra:
        k = sum(bool((r.get(outra) or "").strip()) for r in registros)
        if k:
            itens.append({"rotulo": "Outro", "k": k, **(wilson(k, n) or {})})
    return {"n": n, "itens": itens}


def calcular(dados: dict[str, list[dict]]) -> dict:
    """Roda todas as análises quantitativas. ``dados`` = {"q1": [...], "q2": [...], "q3": [...]}."""
    q1, q2, q3 = (dados.get(k) or [] for k in ("q1", "q2", "q3"))
    grupos = {"q1": contagem_temas(q1), "q2": contagem_temas(q2), "q3": contagem_temas(q3)}
    conc = concordancia(grupos)
    pp = temas_por_pessoa(q1)
    res = {
        "versao": I.VERSAO,
        "temas": [{"id": t["id"], "rotulo": t["label"], "grupo": t["grupo"]} for t in I.TEMAS],
        "grupos": grupos,
        "concordancia": conc,
        "perfil": {v: perfil(q1, v) for v in I.VARIAVEIS_PERFIL},
        "temas_por_pessoa": pp,
        "matriz": matriz_equipe(q3),
        "proporcoes": {
            "q8": _props(q1, "q8", I.OPT["tv"]),
            "q9": _props(q1, "q9", I.OPT["q9"], multipla=True),
            "barreiras": _props(q2, "q8", I.OPT["barreiras"], multipla=True, outra="q8outra"),
            "obstaculos": _props(q3, "q6", I.OPT["obst"], multipla=True, outra="q6outro"),
        },
        "taxa_resposta": {"q2": {"n": len(q2), "total": I.TOTAL_ACS}, "q3": {"n": len(q3), "total": I.TOTAL_EQUIPE}},
    }
    res["metodos"] = texto_metodos(res)
    return res


def texto_metodos(res: dict) -> str:
    g = res["grupos"]
    W = res["concordancia"]["W"]
    kw = res["temas_por_pessoa"]["kruskal"]
    tr = res["taxa_resposta"]
    pct = lambda a, b: f"{round(100 * a / b)}%" if b else ""
    partes = [
        "Os dados quantitativos foram analisados de forma descritiva, com frequências absolutas e relativas. "
        "Para as proporções, foram calculados intervalos de confiança de 95% pelo método de Wilson, mais adequado "
        f"a amostras pequenas e a proporções próximas de 0 ou 1. Participaram {g['q1']['n']} pacientes (Q1), em amostra "
        f"de conveniência, {g['q2']['n']} dos {tr['q2']['total']} agentes comunitários de saúde ({pct(g['q2']['n'], tr['q2']['total'])}; Q2) "
        f"e {g['q3']['n']} dos {tr['q3']['total']} profissionais da equipe ({pct(g['q3']['n'], tr['q3']['total'])}; Q3).",
        f"A mesma lista de {len(I.TEMAS)} temas, organizada em {len(I.Q1T)} grupos, foi apresentada aos três grupos. "
        "Os pacientes podiam marcar quantos temas quisessem; ACS e profissionais marcaram até dois temas por grupo e "
        "indicaram os três mais urgentes. Como as regras de marcação diferem, a comparação entre os grupos considerou "
        "a ordem de prioridade dos temas, e não as proporções absolutas: a concordância foi estimada pelo coeficiente "
        "de correlação de postos de Spearman entre pares de grupos e pelo coeficiente de concordância W de Kendall "
        "entre os três grupos" + (f" (W = {W['W']:.2f}; p {fmt_p(W['p'])})".replace(".", ",", 1) if W else "") + ".",
        "A associação entre o perfil dos pacientes (faixa etária, gênero, tempo de residência no território e atenção "
        "à TV da sala de espera) e a escolha de cada tema foi explorada pelo teste exato de Fisher, para tabelas 2×2, "
        "ou pelo teste qui-quadrado de Pearson, para tabelas maiores. Os valores de p foram corrigidos para comparações "
        "múltiplas pelo procedimento de Benjamini-Hochberg, com taxa de falsas descobertas de 5%. O número de temas "
        "marcados por paciente foi descrito por média, desvio padrão, mediana e intervalo interquartil"
        + (", e comparado entre faixas etárias pelo teste de Kruskal-Wallis" if kw else "") + ".",
        "Na matriz de priorização respondida pela equipe, a frequência na demanda e o potencial de impacto educativo "
        "de cada macro-tema foram avaliados em escala de 1 a 5 e descritos por média, intervalo de confiança de 95% "
        "(distribuição t) e mediana. Dada a natureza exploratória do estudo e o tamanho dos grupos, os testes de "
        "hipótese foram usados para orientar a interpretação, e não para inferência populacional. As análises foram "
        f"feitas em Python (SciPy, statsmodels e pandas), com o código do projeto Fio a Fio versão {I.VERSAO}.",
    ]
    return "\n\n".join(partes)
