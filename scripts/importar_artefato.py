"""Importa para o Supabase os dados coletados no painel de testes (artefato do Claude).

Uso (no seu computador, com .env preenchido):
    python scripts/importar_artefato.py exportacao_artefato.json

O arquivo deve ter a forma {"q1": [...], "q2": [...], "q3": [...], "codes": [...], ...},
com cada registro contendo "id" e os campos da resposta. Registros já existentes
(mesmo id) são atualizados, então o script pode ser rodado mais de uma vez.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analise.dados import TABELAS  # noqa: E402

TABELAS = {**TABELAS, "sug": "sugestoes", "links": "links_online"}


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    url = os.environ["SUPABASE_URL"].rstrip("/")
    chave = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    dados = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    for col, regs in dados.items():
        if col not in TABELAS or not regs:
            continue
        linhas = [{"id": r["id"], "data": {k: v for k, v in r.items() if k != "id"}} for r in regs]
        req = urllib.request.Request(f"{url}/rest/v1/{TABELAS[col]}", data=json.dumps(linhas).encode(), method="POST",
                                     headers={"apikey": chave, "Authorization": f"Bearer {chave}", "Content-Type": "application/json",
                                              "Prefer": "resolution=merge-duplicates"})
        with urllib.request.urlopen(req, timeout=60):
            print(f"{TABELAS[col]}: {len(linhas)} registro(s)")


if __name__ == "__main__":
    main()
