"""Reproduz todas as análises do artigo a partir de uma exportação anonimizada.

Uso:
    python -m analise.dados exportar                      # gera dados/fioafio_anonimizado.json
    python publicacao/analise_publicacao.py dados/fioafio_anonimizado.json

Saída em ``saida/`` (fora do repositório):
    tabela_temas.csv          proporção de cada tema por grupo, com IC 95% de Wilson
    tabela_concordancia.csv   Spearman entre pares e W de Kendall
    tabela_perfil.csv         Fisher / qui-quadrado por tema e variável, com q de BH
    tabela_matriz.csv         matriz da equipe (média, IC 95%, mediana)
    tabela_proporcoes.csv     TV, formato, barreiras e obstáculos
    tematica.json             triangulação, saturação e concordância entre codificadores
    metodos.txt               texto da seção de métodos
    ambiente.txt              versões do Python e das bibliotecas
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analise import estatistica as E  # noqa: E402
from analise import qualitativa as Q  # noqa: E402
from analise.dados import carregar_json  # noqa: E402
from analise.instrumento import VERSAO, VARIAVEIS_PERFIL  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dados", help="exportação em JSON (anonimizada)")
    ap.add_argument("--saida", default="saida")
    a = ap.parse_args()
    out = Path(a.saida)
    out.mkdir(parents=True, exist_ok=True)

    dados = carregar_json(a.dados)
    R = E.calcular(dados)
    temas = R["temas"]

    linhas = []
    for g, s in R["grupos"].items():
        for t, k, u, ic in zip(temas, s["cnt"], s["urg"], s["ic"]):
            linhas.append({"grupo": g.upper(), "tema": t["rotulo"], "grupo_tematico": t["grupo"], "n": s["n"], "marcaram": k,
                           "proporcao": ic and ic["p"], "ic95_inf": ic and ic["lo"], "ic95_sup": ic and ic["hi"],
                           "urgentes": u if g != "q1" else None})
    pd.DataFrame(linhas).to_csv(out / "tabela_temas.csv", index=False, encoding="utf-8-sig")

    C = R["concordancia"]
    conc = [{"comparacao": f"{p['a'].upper()} x {p['b'].upper()}", "estatistica": "rho de Spearman", "valor": p.get("r"),
             "p": p.get("p"), "n_temas": p.get("n")} for p in C["pares"]]
    if C["W"]:
        conc.append({"comparacao": "Q1, Q2 e Q3", "estatistica": "W de Kendall", "valor": C["W"]["W"], "p": C["W"]["p"],
                     "n_temas": C["W"]["n"], "qui2": C["W"]["x"], "gl": C["W"]["df"]})
    pd.DataFrame(conc).to_csv(out / "tabela_concordancia.csv", index=False, encoding="utf-8-sig")

    perf = []
    rot = {t["id"]: t["rotulo"] for t in temas}
    for v, P in R["perfil"].items():
        for l in P["linhas"]:
            row = {"variavel": VARIAVEIS_PERFIL[v]["rotulo"], "tema": rot[l["tema"]], "teste": l["teste"], "p": l["p"], "q_bh": l["q"]}
            for o, (k, nk) in zip(P["opcoes"], l["tab"]):
                row[f"{o} (marcou/total)"] = f"{k}/{k + nk}"
            perf.append(row)
    pd.DataFrame(perf).to_csv(out / "tabela_perfil.csv", index=False, encoding="utf-8-sig")

    mat = []
    for m in R["matriz"]:
        for dim, d in (("frequencia", m["f"]), ("impacto", m["i"])):
            if d:
                mat.append({"macro_tema": m["rotulo"], "dimensao": dim, "n": d["n"], "media": d["media"], "dp": d["dp"],
                            "ic95_inf": d["lo"], "ic95_sup": d["hi"], "mediana": d["mediana"], "q1": d["q1"], "q3": d["q3"]})
    pd.DataFrame(mat).to_csv(out / "tabela_matriz.csv", index=False, encoding="utf-8-sig")

    props = [{"pergunta": k, "categoria": it["rotulo"], "n": P["n"], "marcaram": it["k"], "proporcao": it.get("p"),
              "ic95_inf": it.get("lo"), "ic95_sup": it.get("hi")} for k, P in R["proporcoes"].items() for it in P["itens"]]
    pd.DataFrame(props).to_csv(out / "tabela_proporcoes.csv", index=False, encoding="utf-8-sig")

    if dados.get("cod"):
        T = Q.calcular(dados, dados.get("codes") or [], dados["cod"])
        (out / "tematica.json").write_text(json.dumps(T, ensure_ascii=False, indent=1), encoding="utf-8")

    (out / "metodos.txt").write_text(R["metodos"], encoding="utf-8")
    import numpy, scipy, sklearn, statsmodels  # noqa: E401
    (out / "ambiente.txt").write_text(
        f"Fio a Fio {VERSAO}\nPython {platform.python_version()}\nnumpy {numpy.__version__}\npandas {pd.__version__}\n"
        f"scipy {scipy.__version__}\nstatsmodels {statsmodels.__version__}\nscikit-learn {sklearn.__version__}\n", encoding="utf-8")
    print(f"Pronto: {out}/ (Q1={R['grupos']['q1']['n']}, Q2={R['grupos']['q2']['n']}, Q3={R['grupos']['q3']['n']})")


if __name__ == "__main__":
    main()
