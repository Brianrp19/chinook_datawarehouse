#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
pg_data="$project_dir/.postgres/data"

if [[ ! -f "$pg_data/PG_VERSION" ]]; then
    echo "No existe un clúster PostgreSQL privado para este proyecto."
    exit 0
fi

pg_bin="$(pg_config --bindir)"
if "$pg_bin/pg_ctl" --pgdata="$pg_data" status >/dev/null 2>&1; then
    "$pg_bin/pg_ctl" --pgdata="$pg_data" stop --mode=fast --wait
else
    echo "PostgreSQL ya estaba detenido."
fi
