"""Testes da análise estatística.

1. Valores de referência conferidos à mão ou com SciPy.
2. Paridade com o painel: os dados de exemplo e os resultados calculados pelo
   painel em JavaScript (tests/fixtures/paridade_exemplo.json) precisam bater
   com o Python. Assim, a migração do artefato para o site não muda números.
"""
import json
from pathlib import Path

import pytest

from analise import estatistica as E
from analise import instrumento as I
from analise import qualitativa as Q

FX = json.loads((Path(__file__).parent / "fixtures" / "paridade_exemplo.json").read_text(encoding="utf-8"))
D = FX["dados"]
JS = FX["js"]
TOL = 1e-6


def approx(x):
    return pytest.approx(x, abs=TOL) if x is not None else None


def test_wilson_referencia():
    w = E.wilson(7, 20)
    assert w["p"] == 0.35
    assert w["lo"] == pytest.approx(0.18119, abs=1e-5)
    assert w["hi"] == pytest.approx(0.56715, abs=1e-5)


def test_fisher_e_qui_quadrado_referencia():
    assert E.fisher([[8, 2], [1, 5]]) == pytest.approx(0.034965, abs=1e-6)
    c = E.qui_quadrado([[10, 5], [3, 12], [6, 6]])
    assert c["x"] == pytest.approx(6.746911, abs=1e-6) and c["df"] == 2
    assert c["p"] == pytest.approx(0.034271, abs=1e-6)


def test_kendall_w_concordancia_perfeita():
    w = E.kendall_w([[5, 4, 3, 2, 1], [10, 8, 6, 4, 2], [1.0, .8, .6, .4, .2]])
    assert w["W"] == pytest.approx(1.0)


def test_benjamini_hochberg_ignora_ausentes():
    q = E.benjamini_hochberg([0.01, None, 0.04, 0.03])
    assert q[1] is None and q[0] == pytest.approx(0.03)


def test_paridade_wilson_temas_q1():
    g = E.contagem_temas(D["q1"])
    for ic, js in zip(g["ic"], JS["wil"]):
        # O painel usava z = 1,96; o statsmodels usa o quantil exato (1,959964). Diferença < 1e-5.
        assert ic["lo"] == pytest.approx(js["lo"], abs=1e-5) and ic["hi"] == pytest.approx(js["hi"], abs=1e-5)


def test_paridade_spearman_e_kendall():
    res = E.calcular(D)
    pares = {(p["a"], p["b"]): p for p in res["concordancia"]["pares"]}
    for js in JS["pairs"]:
        py = pares[(js["a"], js["b"])]
        assert py["r"] == approx(js["r"])
        assert py["p"] == pytest.approx(js["p"], rel=1e-6, abs=1e-12)
    W = res["concordancia"]["W"]
    assert W["W"] == approx(JS["W"]["W"]) and W["p"] == pytest.approx(JS["W"]["p"], rel=1e-6, abs=1e-12)


@pytest.mark.parametrize("var", list(I.VARIAVEIS_PERFIL))
def test_paridade_perfil(var):
    py = E.perfil(D["q1"], var)["linhas"]
    for linha, pj, qj in zip(py, JS["prof"][var], JS["prof"][var + "_q"]):
        if pj is None:
            assert linha["p"] is None
        else:
            assert linha["p"] == pytest.approx(pj, rel=1e-6, abs=1e-10)
            assert linha["q"] == pytest.approx(qj, rel=1e-6, abs=1e-10)


def test_paridade_kruskal():
    kw = E.temas_por_pessoa(D["q1"])["kruskal"]
    assert kw["H"] == approx(JS["kw"]["H"]) and kw["p"] == pytest.approx(JS["kw"]["p"], rel=1e-6)


def test_paridade_matriz():
    py = {m["id"]: m for m in E.matriz_equipe(D["q3"])}
    for js in JS["mx"]:
        for k in ("f", "i"):
            a, b = py[js["id"]][k], js[k]
            assert a["media"] == approx(b["mean"]) and a["dp"] == approx(b["sd"])
            assert a["mediana"] == approx(b["med"]) and a["lo"] == approx(b["lo"]) and a["hi"] == approx(b["hi"])


def test_paridade_qualitativa():
    T = FX["tema"]
    units = Q.unidades(D)
    assert len(units) == T["nUnits"]
    final = Q.codificacao_final(T["cod"])
    tri = {l["categoria"]: l["cnt"] for l in Q.triangulacao(units, T["codes"], final)["linhas"]}
    assert tri == T["tri"]
    assert Q.saturacao(units, final) == T["curve"]
    conc = Q.concordancia(units, T["cod"], "exemplo-a", "exemplo-b")
    assert conc["n"] == T["ncommon"]
    for p in conc["por_codigo"]:
        js = T["kap"][p["codigo"]]
        assert (p["kappa"] is None and js is None) or p["kappa"] == approx(js)


def test_resultado_e_serializavel():
    json.dumps(E.calcular(D), allow_nan=False)
    json.dumps(Q.calcular(D, FX["tema"]["codes"], FX["tema"]["cod"]), allow_nan=False)


def test_instrumento_igual_ao_site():
    """As listas de temas do site precisam ser as mesmas do instrumento.json."""
    html = (Path(__file__).parents[1] / "web" / "index.html").read_text(encoding="utf-8")
    for t in I.TEMAS:
        assert f'["{t["id"]}","{t["label"]}","{t["macro"]}"]' in html, t["id"]
