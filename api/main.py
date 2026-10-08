"""API do Projeto Fio a Fio (versão 1.0).

Calculadora em Python para o site: recebe os registros que o painel já leu do
Supabase (o administrador só lê o que as regras do banco permitem) e devolve
as análises. Também faz a ponte com a API do Claude, para que a chave nunca
fique no navegador.

Rotas:
  GET  /api/saude          status e versão
  POST /api/estatistica    análises quantitativas   (administrador)
  POST /api/tematica       métricas da análise temática (administrador)
  POST /api/claude         sugestões de códigos e rascunhos (administrador)
"""
from __future__ import annotations

import json
import os
import re
import time

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from analise import estatistica, qualitativa
from analise.instrumento import VERSAO

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5")
SEM_AUTH = os.environ.get("FIO_DEV_SEM_AUTH") == "1"  # só para desenvolvimento local
ORIGENS = [o.strip() for o in os.environ.get("WEB_ORIGIN", "*").split(",") if o.strip()]

app = FastAPI(title="Fio a Fio API", version=VERSAO)
app.add_middleware(CORSMiddleware, allow_origins=ORIGENS, allow_methods=["GET", "POST"],
                   allow_headers=["Authorization", "Content-Type"])

_cache: dict[str, tuple[float, str]] = {}


async def exigir_admin(authorization: str | None = Header(default=None)) -> str:
    """Confere o token do Supabase e se a pessoa tem papel de administrador."""
    if SEM_AUTH:
        return "dev"
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Faça login no painel.")
    token = authorization.split(" ", 1)[1]
    hit = _cache.get(token)
    if hit and hit[0] > time.time():
        return hit[1]
    h = {"apikey": SUPABASE_ANON_KEY, "Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=15) as c:
        u = await c.get(f"{SUPABASE_URL}/auth/v1/user", headers=h)
        if u.status_code != 200:
            raise HTTPException(401, "Sessão expirada. Entre de novo.")
        uid = u.json()["id"]
        p = await c.get(f"{SUPABASE_URL}/rest/v1/perfis", params={"id": f"eq.{uid}", "select": "papel"}, headers=h)
    if p.status_code != 200 or not p.json() or p.json()[0].get("papel") != "admin":
        raise HTTPException(403, "Acesso só para administradores.")
    _cache[token] = (time.time() + 300, uid)
    return uid


class Dados(BaseModel):
    q1: list[dict] = Field(default_factory=list)
    q2: list[dict] = Field(default_factory=list)
    q3: list[dict] = Field(default_factory=list)


class DadosTematica(Dados):
    codes: list[dict] = Field(default_factory=list)
    cod: list[dict] = Field(default_factory=list)
    par: list[str] | None = None


class Pedido(BaseModel):
    prompt: str = Field(max_length=200_000)
    json_: bool = Field(default=False, alias="json")
    nivel: str = "default"


@app.get("/api/saude")
def saude():
    return {"ok": True, "versao": VERSAO, "claude": bool(ANTHROPIC_API_KEY)}


@app.post("/api/estatistica")
def rota_estatistica(d: Dados, _=Depends(exigir_admin)):
    return estatistica.calcular(d.model_dump())


@app.post("/api/tematica")
def rota_tematica(d: DadosTematica, _=Depends(exigir_admin)):
    par = tuple(d.par) if d.par and len(d.par) == 2 else None
    return qualitativa.calcular(d.model_dump(include={"q1", "q2", "q3"}), d.codes, d.cod, par)


def _extrair_json(texto: str):
    m = re.search(r"\{[\s\S]*\}", texto)
    if not m:
        raise HTTPException(502, "A resposta do Claude não veio em JSON.")
    return json.loads(m.group(0))


@app.post("/api/claude")
async def rota_claude(p: Pedido, _=Depends(exigir_admin)):
    if not ANTHROPIC_API_KEY:
        raise HTTPException(503, "Chave da API do Claude não configurada no servidor.")
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.post("https://api.anthropic.com/v1/messages",
                         headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01",
                                  "content-type": "application/json"},
                         json={"model": ANTHROPIC_MODEL, "max_tokens": 4096,
                               "messages": [{"role": "user", "content": p.prompt}]})
    if r.status_code == 429:
        raise HTTPException(429, "Muitas solicitações seguidas.")
    if r.status_code != 200:
        raise HTTPException(502, "Falha ao consultar o Claude.")
    texto = "".join(b.get("text", "") for b in r.json().get("content", []) if b.get("type") == "text")
    return {"text": texto, "json": _extrair_json(texto) if p.json_ else None}
