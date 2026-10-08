"""Métricas da análise de conteúdo temática (Bardin; leitura freireana).

A codificação é feita por pessoas no site. Este módulo só calcula, a partir das
codificações registradas:
  * as unidades de registro (cada resposta aberta);
  * a codificação final de cada unidade (consenso, ou união dos codificadores);
  * a triangulação das categorias entre as três escutas;
  * a curva de saturação;
  * a concordância entre dois codificadores (concordância exata, Jaccard e
    kappa de Cohen por código, com leitura de Landis e Koch, 1977).
"""
from __future__ import annotations

import math
from collections import defaultdict

from sklearn.metrics import cohen_kappa_score

from . import instrumento as I

CONSENSO = "consenso"


def unidades(dados: dict[str, list[dict]]) -> list[dict]:
    """Cada resposta aberta vira uma unidade com chave estável ``q.registro.campo.indice``."""
    out = []
    for q, campo, nuc, *tipo in I.UDEF:
        tipo = tipo[0] if tipo else None
        for r in dados.get(q) or []:
            rid = r.get("id") or r.get("code")
            v = r.get(campo)
            if tipo == "tcl":
                vals = [(x or {}).get("t") for x in (v or [])]
            elif tipo == "arr":
                vals = list(v or [])
            else:
                vals = [v]
            for i, t in enumerate(vals):
                if t and str(t).strip():
                    out.append({"key": f"{q}.{rid}.{campo}.{i}", "t": str(t).strip(), "q": q,
                                "src": q.upper(), "rcode": r.get("code") or "?", "nuc": nuc,
                                "data": r.get("data") or ""})
    return out


def codificacao_final(cod: list[dict]) -> dict[str, list[str]]:
    """Consenso, quando houver; senão, a união dos códigos de todos os codificadores."""
    por_unidade: dict[str, dict[str, list[str]]] = defaultdict(dict)
    for c in cod:
        por_unidade[c["unit"]][c["coder"]] = list(c.get("codes") or [])
    final = {}
    for u, porc in por_unidade.items():
        final[u] = porc[CONSENSO] if CONSENSO in porc else sorted({x for v in porc.values() for x in v})
    return final


def triangulacao(units: list[dict], codes: list[dict], final: dict[str, list[str]]) -> dict:
    cat_de = {c["id"]: (c.get("cat") or "Sem categoria") for c in codes}
    codificadas = [u for u in units if final.get(u["key"])]
    por_src = {s: sum(u["src"] == s for u in codificadas) for s in ("Q1", "Q2", "Q3")}
    linhas = []
    for cat in sorted(set(cat_de.values())):
        ids = {i for i, c in cat_de.items() if c == cat}
        cnt = {s: 0 for s in por_src}
        for u in codificadas:
            if ids & set(final[u["key"]]):
                cnt[u["src"]] += 1
        por_codigo = []
        for c in codes:
            if c["id"] in ids:
                k = {s: sum(c["id"] in final[u["key"]] and u["src"] == s for u in codificadas) for s in por_src}
                por_codigo.append({"id": c["id"], "nome": c.get("name"), "cnt": k})
        nsrc = sum(v > 0 for v in cnt.values())
        linhas.append({"categoria": cat, "cnt": cnt,
                       "pct": {s: (cnt[s] / por_src[s] if por_src[s] else 0) for s in cnt},
                       "escutas": nsrc, "codigos": por_codigo})
    linhas.sort(key=lambda l: (-l["escutas"], -sum(l["cnt"].values())))
    return {"unidades_codificadas": por_src, "linhas": linhas}


def saturacao(units: list[dict], final: dict[str, list[str]]) -> list[int]:
    """Códigos distintos acumulados por unidade codificada, em ordem de coleta."""
    cod = [u for u in units if final.get(u["key"])]
    cod.sort(key=lambda u: (u["data"], _ord(u["rcode"])))
    vistos, curva = set(), []
    for u in cod:
        vistos.update(final[u["key"]])
        curva.append(len(vistos))
    return curva


def _ord(code: str):
    digitos = "".join(ch for ch in code if ch.isdigit())
    return (code[:1], int(digitos) if digitos else 0)


def leitura_kappa(k: float | None) -> str:
    if k is None:
        return ""
    return ("pior que o acaso" if k < 0 else "leve" if k < .21 else "razoável" if k < .41
            else "moderada" if k < .61 else "substancial" if k < .81 else "quase perfeita")


def concordancia(units: list[dict], cod: list[dict], a: str, b: str) -> dict:
    validas = {u["key"] for u in units}
    A = {c["unit"]: set(c.get("codes") or []) for c in cod if c["coder"] == a}
    B = {c["unit"]: set(c.get("codes") or []) for c in cod if c["coder"] == b}
    comuns = sorted(k for k in A if k in B and k in validas)
    n = len(comuns)
    if not n:
        return {"a": a, "b": b, "n": 0, "exata": None, "jaccard": None, "kappa_medio": None, "por_codigo": [], "divergencias": []}
    exatas = sum(A[k] == B[k] for k in comuns)
    jac = sum((len(A[k] & B[k]) / len(A[k] | B[k])) if (A[k] | B[k]) else 1 for k in comuns) / n
    usados = sorted({x for k in comuns for x in A[k] | B[k]})
    por = []
    for cid in usados:
        xa = [int(cid in A[k]) for k in comuns]
        xb = [int(cid in B[k]) for k in comuns]
        k = cohen_kappa_score(xa, xb) if len(set(xa) | set(xb)) > 1 else float("nan")
        k = None if math.isnan(k) else float(k)
        por.append({"codigo": cid, "ambos": sum(p and q for p, q in zip(xa, xb)),
                    "so_a": sum(p and not q for p, q in zip(xa, xb)), "so_b": sum(q and not p for p, q in zip(xa, xb)),
                    "kappa": k, "leitura": leitura_kappa(k)})
    ks = [p["kappa"] for p in por if p["kappa"] is not None]
    km = sum(ks) / len(ks) if ks else None
    por.sort(key=lambda p: (p["kappa"] if p["kappa"] is not None else 2))
    return {"a": a, "b": b, "n": n, "exata": exatas / n, "jaccard": jac, "kappa_medio": km,
            "leitura_media": leitura_kappa(km), "por_codigo": por,
            "divergencias": [k for k in comuns if A[k] != B[k]]}


def calcular(dados: dict, codes: list[dict], cod: list[dict], par: tuple[str, str] | None = None) -> dict:
    units = unidades(dados)
    final = codificacao_final(cod)
    codificadores = sorted({c["coder"] for c in cod if c["coder"] != CONSENSO})
    if par is None and len(codificadores) >= 2:
        par = (codificadores[0], codificadores[1])
    return {"versao": I.VERSAO, "n_unidades": len(units),
            "n_codificadas": sum(bool(final.get(u["key"])) for u in units),
            "triangulacao": triangulacao(units, codes, final),
            "saturacao": saturacao(units, final),
            "codificadores": codificadores,
            "concordancia": concordancia(units, cod, *par) if par else None}
