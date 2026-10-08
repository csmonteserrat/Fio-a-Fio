"""Definições do instrumento (questionários Q1, Q2 e Q3 do Projeto Fio a Fio).

A fonte única é ``instrumento.json``, gerado a partir do painel. Os testes
conferem se o site (web/index.html) usa exatamente as mesmas definições.
"""
from __future__ import annotations

import json
from pathlib import Path

_DADOS = json.loads((Path(__file__).with_name("instrumento.json")).read_text(encoding="utf-8"))

VERSAO: str = _DADOS["versao"]
MACROS: list[dict] = _DADOS["MACROS"]
MX: list[dict] = [m for m in MACROS if m["id"] != "outro"]
MACRO_LABEL: dict[str, str] = {m["id"]: m["label"] for m in MACROS}
Q1T: list[dict] = _DADOS["Q1T"]
TEMAS: list[dict] = [dict(item, grupo=g["cat"]) for g in Q1T for item in g["items"]]
TEMA_IDS: list[str] = [t["id"] for t in TEMAS]
TEMA_MACRO: dict[str, str] = {t["id"]: t["macro"] for t in TEMAS}
OPT: dict[str, list[str]] = _DADOS["OPT"]
STAFF: dict[str, list[str]] = _DADOS["STAFF"]
ANON: str = _DADOS["ANON"]
NUC: dict[str, str] = _DADOS["NUC"]
UDEF: list[list[str]] = _DADOS["UDEF"]
NUCTYPE: dict[str, str] = _DADOS["NUCTYPE"]

#: Totais para o cálculo da taxa de resposta (censo de ACS e equipe).
TOTAL_ACS = len(STAFF["Agente Comunitário de Saúde"])
TOTAL_EQUIPE = sum(len(v) for k, v in STAFF.items() if k != "Agente Comunitário de Saúde")

#: Variáveis de perfil dos pacientes usadas na análise exploratória.
VARIAVEIS_PERFIL = {
    "idade": {"rotulo": "Faixa etária", "opcoes": OPT["idade"]},
    "genero": {"rotulo": "Gênero (feminino x masculino)", "opcoes": ["Feminino", "Masculino"]},
    "tempo": {"rotulo": "Tempo no território", "opcoes": OPT["tempoT"]},
    "q8": {"rotulo": "Atenção à TV", "opcoes": OPT["tv"]},
}
