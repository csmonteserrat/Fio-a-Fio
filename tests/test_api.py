"""Testes da API (sem login, modo de desenvolvimento)."""
import json
import os
import re
from pathlib import Path

os.environ["FIO_DEV_SEM_AUTH"] = "1"

from fastapi.testclient import TestClient  # noqa: E402

from api.main import app  # noqa: E402

FX = json.loads((Path(__file__).parent / "fixtures" / "paridade_exemplo.json").read_text(encoding="utf-8"))
cli = TestClient(app)
RAIZ = Path(__file__).parents[1]


def test_saude_e_versao():
    r = cli.get("/api/saude").json()
    assert r["ok"] and r["versao"] == (RAIZ / "VERSION").read_text().strip()


def test_estatistica():
    r = cli.post("/api/estatistica", json=FX["dados"])
    assert r.status_code == 200
    j = r.json()
    assert j["grupos"]["q1"]["n"] == len(FX["dados"]["q1"])
    assert abs(j["concordancia"]["W"]["W"] - FX["js"]["W"]["W"]) < 1e-9


def test_estatistica_vazia():
    r = cli.post("/api/estatistica", json={})
    assert r.status_code == 200 and r.json()["concordancia"]["W"] is None


def test_tematica():
    T = FX["tema"]
    r = cli.post("/api/tematica", json={**FX["dados"], "codes": T["codes"], "cod": T["cod"]})
    assert r.status_code == 200
    assert r.json()["saturacao"] == T["curve"]


def test_claude_sem_chave():
    assert cli.post("/api/claude", json={"prompt": "oi"}).status_code == 503


def test_versao_do_site_igual_ao_arquivo_VERSION():
    html = (RAIZ / "web" / "index.html").read_text(encoding="utf-8")
    v = re.search(r'const FIO_VERSAO="([^"]+)"', html).group(1)
    assert (RAIZ / "VERSION").read_text().strip().startswith(v)
