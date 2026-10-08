"""Carregamento e anonimização dos dados.

Os dados vivem no Supabase. Para a publicação, exporte uma cópia anonimizada
com ``python -m analise.dados exportar`` e rode as análises sobre ela. Nunca
coloque dados no repositório (a pasta ``dados/`` está no .gitignore).
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.request
from pathlib import Path

#: Coleções do site e as tabelas correspondentes no Supabase.
TABELAS = {"q1": "respostas_q1", "q2": "respostas_q2", "q3": "respostas_q3",
           "codes": "codigos", "cats": "categorias", "cod": "codificacoes", "temas": "temas_geradores"}

#: Campos que identificam pessoas e saem na anonimização.
CAMPOS_PESSOAIS = ("resp", "aplicador", "editadoPor")


def _rest(url: str, chave: str, tabela: str) -> list[dict]:
    req = urllib.request.Request(f"{url.rstrip('/')}/rest/v1/{tabela}?select=id,data&order=created_at.asc",
                                 headers={"apikey": chave, "Authorization": f"Bearer {chave}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return [{"id": x["id"], **(x.get("data") or {})} for x in json.loads(r.read())]


def carregar_supabase(url: str | None = None, chave: str | None = None) -> dict[str, list[dict]]:
    """Lê todas as tabelas com a chave de serviço (só no computador da pesquisa, nunca no navegador)."""
    url = url or os.environ["SUPABASE_URL"]
    chave = chave or os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return {k: _rest(url, chave, t) for k, t in TABELAS.items()}


def carregar_json(caminho: str | Path) -> dict[str, list[dict]]:
    return json.loads(Path(caminho).read_text(encoding="utf-8"))


def anonimizar(dados: dict[str, list[dict]]) -> dict[str, list[dict]]:
    """Troca nomes de respondentes e aplicadores por pseudônimos estáveis (R01, AP01...).

    Atenção: respostas abertas podem conter nomes ou detalhes identificáveis
    escritos pelos participantes. Revise as falas antes de divulgar.
    """
    pseud: dict[str, str] = {}

    def p(nome: str, pref: str) -> str:
        if not nome:
            return ""
        chave = pref + nome
        if chave not in pseud:
            pseud[chave] = f"{pref}{sum(k.startswith(pref) for k in pseud) + 1:02d}"
        return pseud[chave]

    out = {}
    for k, regs in dados.items():
        novos = []
        for r in regs:
            r = dict(r)
            if k in ("q2", "q3"):
                r["resp"] = "anônimo" if r.get("resp") in ("", None, "Prefere não se identificar") else p(r.get("resp", ""), "R")
            if r.get("aplicador"):
                r["aplicador"] = "online" if r["aplicador"].startswith("Online") else p(r["aplicador"], "AP")
            r.pop("editadoPor", None)
            novos.append(r)
        out[k] = novos
    if "cod" in out:
        for c in out["cod"]:
            if c.get("coder") not in ("consenso", None):
                c["coder"] = p(c["coder"], "C")
    return out


def main():
    ap = argparse.ArgumentParser(description="Exporta os dados do Supabase para análise.")
    ap.add_argument("acao", choices=["exportar"])
    ap.add_argument("--saida", default="dados/fioafio_anonimizado.json")
    ap.add_argument("--sem-anonimizar", action="store_true", help="mantém nomes (só para uso interno)")
    a = ap.parse_args()
    dados = carregar_supabase()
    if not a.sem_anonimizar:
        dados = anonimizar(dados)
    Path(a.saida).parent.mkdir(parents=True, exist_ok=True)
    Path(a.saida).write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{a.saida}: " + ", ".join(f"{k}={len(v)}" for k, v in dados.items()))


if __name__ == "__main__":
    main()
