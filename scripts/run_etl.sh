#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

if [[ ! -f .env ]]; then
    echo "Error: falta .env. Ejecuta primero ./scripts/setup_local.sh" >&2
    exit 1
fi

set -a
source .env
set +a

export PREFECT_HOME="$project_dir/.prefect"
export PREFECT_SERVER_ANALYTICS_ENABLED=false

pg_data="$project_dir/.postgres/data"
if [[ ! -f "$pg_data/PG_VERSION" ]]; then
    echo "Error: PostgreSQL local no está configurado. Ejecuta ./scripts/setup_local.sh" >&2
    exit 1
fi

pg_bin="$(pg_config --bindir)"
mkdir -p "$PGHOST"
chmod 700 "$PGHOST"
if ! "$pg_bin/pg_isready" --host="$PGHOST" --port="$PGPORT" >/dev/null 2>&1; then
    echo "Iniciando PostgreSQL privado..."
    "$pg_bin/pg_ctl" --pgdata="$pg_data" \
        --log="$project_dir/.postgres/postgresql.log" \
        --options="-k $PGHOST -p $PGPORT -c listen_addresses=" start --wait
fi

.venv/bin/python src/etl_flow.py
