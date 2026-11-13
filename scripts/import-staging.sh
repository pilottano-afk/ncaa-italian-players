#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAGING_DIR="${1:-$ROOT_DIR/data/staging/2027}"
DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://ncaa:ncaa@localhost:5432/ncaa_players}"

cd "$ROOT_DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker non trovato. Installa/avvia Docker e riprova." >&2
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose non disponibile. Verifica l'installazione di Docker Compose." >&2
  exit 1
fi
for required in manifest.json quality-audit.json; do
  if [[ ! -f "$STAGING_DIR/$required" ]]; then
    echo "File mancante: $STAGING_DIR/$required" >&2
    echo "Estrai prima lo ZIP completo dello staging in data/staging/2027/." >&2
    exit 1
  fi
done

echo "Avvio PostgreSQL locale..."
docker compose up -d db

echo "Installazione del progetto nell'ambiente Python attivo..."
python -m pip install -e .

echo "Import controllato dei dati NCAA 2026-27..."
DATABASE_URL="$DATABASE_URL" ncaa-import-raw --input "$STAGING_DIR"

echo "Importazione terminata. Per controllare i conteggi:"
echo "docker compose exec db psql -U ncaa -d ncaa_players"
