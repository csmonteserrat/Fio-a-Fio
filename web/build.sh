#!/bin/sh
# Gera web/config.js a partir das variáveis de ambiente do Render.
set -e
: "${SUPABASE_URL:?defina SUPABASE_URL}"
: "${SUPABASE_ANON_KEY:?defina SUPABASE_ANON_KEY}"
: "${API_URL:?defina API_URL}"
# remove espaços e barras coladas por engano nas variáveis
API_URL=$(printf %s "$API_URL" | tr -d ' \t\r\n' | sed 's:/*$::')
SUPABASE_URL=$(printf %s "$SUPABASE_URL" | tr -d ' \t\r\n' | sed 's:/*$::')
SUPABASE_ANON_KEY=$(printf %s "$SUPABASE_ANON_KEY" | tr -d ' \t\r\n')
cat > web/config.js <<CFG
window.FIO_CONFIG = {
  SUPABASE_URL: "${SUPABASE_URL}",
  SUPABASE_ANON_KEY: "${SUPABASE_ANON_KEY}",
  API_URL: "${API_URL}",
  DOMINIO_EMAIL: "${DOMINIO_EMAIL:-fioafio.app}",
  AVALIADOR_EMAIL: "${AVALIADOR_EMAIL:-avaliador@fioafio.app}"
};
CFG
echo "config.js gerado (versão $(cat VERSION))"
