import json
import os
from pathlib import Path
import sys
import urllib.request

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')


def check_database(label, staging=False):
    names = (
        ['STG_HOST', 'STG_PORT', 'STG_DATABASE', 'STG_USER', 'STG_PASSWORD']
        if staging else ['PGHOST', 'PGPORT', 'PGDATABASE', 'PGUSER', 'PGPASSWORD']
    )
    values = [os.getenv(name, '') for name in names]
    missing = [name for name, value in zip(names, values)
               if not value or value.startswith('cambiar_por_')]
    if missing:
        print(f'[PENDIENTE] {label}: configurar {", ".join(missing)} en .env')
        return False
    host, port, database, user, password = values
    engine = None
    try:
        url = URL.create('postgresql+psycopg', username=user, password=password,
                         host=host, port=int(port), database=database)
        options = {'connect_timeout': 5}
        if staging:
            options['sslmode'] = os.getenv('STG_SSLMODE', 'prefer')
        engine = create_engine(url, connect_args=options)
        with engine.connect().execution_options(isolation_level='REPEATABLE READ') as conn:
            with conn.begin():
                conn.execute(text('SET TRANSACTION READ ONLY'))
                conn.execute(text('SELECT 1'))
                print(f'[OK] {label}: conexión autenticada')
                if staging:
                    contract = json.loads((ROOT / 'contracts/staging_sources.json').read_text(encoding='utf-8'))
                    role = conn.execute(text('SELECT rolsuper, rolcreatedb, rolcreaterole FROM pg_roles WHERE rolname = current_user')).one()
                    safe = not any(role)
                    for source in contract['sources']:
                        table = f'{contract["schema"]}.{source["table"]}'
                        readable = conn.execute(text('SELECT has_table_privilege(current_user, :table, \'SELECT\')'), {'table': table}).scalar()
                        writable = conn.execute(text("SELECT has_table_privilege(current_user, :table, 'INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')"), {'table': table}).scalar()
                        schema_create = conn.execute(text("SELECT has_schema_privilege(current_user, :schema, 'CREATE')"), {'schema': contract['schema']}).scalar()
                        count = len(conn.execute(text(source['query'])).fetchall())
                        valid = readable and not writable and not schema_create and count == source['rows']
                        safe = safe and valid
                        print(f'[{"OK" if valid else "ERROR"}] {source["table"]}: {count}/{source["rows"]} filas; SELECT={bool(readable)}; escritura={bool(writable)}; CREATE esquema={bool(schema_create)}')
                    return safe
                for table in ['dim_date', 'dim_employee', 'dim_customer', 'dim_track', 'fact_sales']:
                    exists = conn.execute(text('SELECT to_regclass(:table)'), {'table': f'public.{table}'}).scalar()
                    if exists is None:
                        print(f'[PENDIENTE] {table}: tabla ausente; no se crea automáticamente')
                        return False
                    count = conn.execute(text(f'SELECT COUNT(*) FROM public.{table}')).scalar()
                    print(f'[INFO] {table}: {count} filas existentes; conservar antes de reconstruir')
        return True
    except Exception as exc:
        # No imprimir excepciones de conexión: pueden contener información sensible.
        print(f'[ERROR] {label}: no se completó la comprobación ({type(exc).__name__}); revisar servicio, credenciales, esquema y permisos')
        return False
    finally:
        if engine is not None:
            engine.dispose()


def main():
    print(f'Python: {sys.version.split()[0]}')
    results = [check_database('Staging', staging=True), check_database('Data Warehouse')]
    api = os.getenv('PREFECT_API_URL', '').rstrip('/')
    try:
        if not api:
            raise ValueError('PREFECT_API_URL ausente')
        with urllib.request.urlopen(api + '/health', timeout=5) as response:
            healthy = response.status == 200
        print(f'[{"OK" if healthy else "ERROR"}] API Prefect')
        results.append(healthy)
    except Exception as exc:
        print(f'[PENDIENTE] API Prefect: sin conexión ({type(exc).__name__})')
        results.append(False)
    return 0 if all(results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
