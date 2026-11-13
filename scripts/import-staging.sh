#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INPUT_PATH="${1:-$ROOT_DIR/data/staging/2027}"
DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://ncaa:ncaa@localhost:5432/ncaa_players}"
TEMP_DIR=""

cleanup() {
  if [[ -n "$TEMP_DIR" && -d "$TEMP_DIR" ]]; then
    rm -rf "$TEMP_DIR"
  fi
}
trap cleanup EXIT

cd "$ROOT_DIR"

if [[ -f "$INPUT_PATH" && "$INPUT_PATH" == *.zip ]]; then
  if ! command -v unzip >/dev/null 2>&1; then
    echo "Il comando unzip non è disponibile. Installa unzip o estrai lo ZIP manualmente." >&2
    exit 1
  fi
  TEMP_DIR="$(mktemp -d)"
  echo "Verifica ed estrazione dello ZIP in una cartella temporanea..."
  unzip -q "$INPUT_PATH" -d "$TEMP_DIR"
  STAGING_DIR="$TEMP_DIR"
else
  STAGING_DIR="$INPUT_PATH"
fi

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
    echo "Passa lo ZIP completo oppure la cartella estratta dello staging." >&2
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
