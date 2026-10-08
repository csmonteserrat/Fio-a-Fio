#!/bin/sh
# Gera web/config.js a partir das variáveis de ambiente do Render.
set -e
: "${SUPABASE_URL:?defina SUPABASE_URL}"
: "${SUPABASE_ANON_KEY:?defina SUPABASE_ANON_KEY}"
: "${API_URL:?defina API_URL}"
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
