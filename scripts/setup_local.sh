#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

for command_name in python3 psql pg_config; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
        echo "Error: falta el comando requerido: ${command_name}" >&2
        exit 1
    fi
done

if [[ ! -x .venv/bin/python ]]; then
    python3 -m venv .venv
fi

echo "Instalando dependencias de Python..."
.venv/bin/python -m pip install -r requirements.txt

pg_bin="$(pg_config --bindir)"
pg_data="$project_dir/.postgres/data"
pg_log="$project_dir/.postgres/postgresql.log"
db_user="$(id -un)"
pg_socket="/tmp/chinook_pg_${db_user}"
pg_port="55432"

if [[ ! "$db_user" =~ ^[a-z_][a-z0-9_-]*$ ]]; then
    echo "Error: nombre de usuario local no compatible con PostgreSQL: ${db_user}" >&2
    exit 1
fi

mkdir -p "$project_dir/.postgres" "$pg_socket"
chmod 700 "$pg_socket"

if [[ ! -f "$pg_data/PG_VERSION" ]]; then
    echo "Creando clúster PostgreSQL privado..."
    "$pg_bin/initdb" --pgdata="$pg_data" --username="$db_user" \
        --auth-local=trust --auth-host=scram-sha-256 --encoding=UTF8 --no-locale
fi

if ! "$pg_bin/pg_isready" --host="$pg_socket" --port="$pg_port" >/dev/null 2>&1; then
    echo "Iniciando PostgreSQL privado en el puerto ${pg_port}..."
    "$pg_bin/pg_ctl" --pgdata="$pg_data" --log="$pg_log" \
        --options="-k $pg_socket -p $pg_port -c listen_addresses=" start --wait
fi

if ! psql --host="$pg_socket" --port="$pg_port" --username="$db_user" \
    --dbname=postgres --tuples-only --no-align \
    --command="SELECT 1 FROM pg_database WHERE datname = 'chinook_dw'" | grep -qx 1; then
    echo "Creando base de datos chinook_dw..."
    "$pg_bin/createdb" --host="$pg_socket" --port="$pg_port" \
        --username="$db_user" --owner="$db_user" chinook_dw
fi

printf '%s\n' \
    "PGHOST=$pg_socket" \
    "PGPORT=$pg_port" \
    "PGUSER=$db_user" \
    "PGDATABASE=chinook_dw" \
    "PREFECT_SERVER_ANALYTICS_ENABLED=false" > .env

echo "Creando el esquema dimensional..."
psql --host="$pg_socket" --port="$pg_port" --username="$db_user" \
    --dbname=chinook_dw --set=ON_ERROR_STOP=1 --file=sql/create_dw.sql

echo "Ejecutando y validando el ETL..."
./scripts/run_etl.sh

echo
echo "Entorno listo. Para volver a ejecutar el flujo:"
echo "  ./scripts/run_etl.sh"
echo "Para detener PostgreSQL:"
echo "  ./scripts/stop_local_postgres.sh"
