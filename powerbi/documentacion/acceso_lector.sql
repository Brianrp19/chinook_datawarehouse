-- OPCIONAL: cuenta de solo lectura para Power BI.
-- Ejecutar TODO este archivo en Query Tool de pgAdmin, conectado a chinook_dw,
-- con un administrador autorizado. También admite psql -d chinook_dw -f archivo.sql.
-- Este archivo no se ejecuta al abrir Power BI y no modifica ventas ni dimensiones.
-- Si el rol ya existe, detenerse y revisar sus permisos antes de reutilizarlo.

BEGIN;

DO $$
BEGIN
    IF current_database() <> 'chinook_dw' THEN
        RAISE EXCEPTION 'Abrir Query Tool sobre chinook_dw antes de ejecutar este archivo';
    END IF;
END
$$;

CREATE ROLE chinook_bi_reader
    LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;

GRANT CONNECT ON DATABASE chinook_dw TO chinook_bi_reader;
GRANT USAGE ON SCHEMA public TO chinook_bi_reader;
GRANT SELECT ON public.fact_sales, public.dim_date, public.dim_customer,
    public.dim_track, public.dim_employee TO chinook_bi_reader;

COMMIT;

-- Luego, dentro de psql conectado a PostgreSQL 18, asignar la contraseña con:
-- \password chinook_bi_reader
-- En pgAdmin también se puede usar Login/Group Roles > chinook_bi_reader >
-- Properties > Definition > Password. No guardar contraseñas dentro de este SQL.
