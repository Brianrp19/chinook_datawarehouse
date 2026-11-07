import pandas as pd 

def validar_modelo_dw(data_dict: dict) -> None:
    print("Iniciando validación del modelo Data Warehouse...")
    # vaslidar tablas antes de cargar tablas en el data warehouse

    tablas_esperadas = {
        "dim_date",
        "dim_employee",
        "dim_customer",
        "dim_track",
        "fact_sales"
    }

    claves_primarias = {
        "dim_date": "date_key",
        "dim_employee": "employee_key",
        "dim_customer": "customer_key",
        "dim_track": "track_key",
        "fact_sales": "sales_key",
    }

    columnas_obligatorias = {
        "dim_date": [
            "full_date", "year", "quarter", "month", "month_name",
            "day", "day_name", "day_of_week", "is_weekend",
        ],
        "dim_employee": [
            "employee_id", "first_name", "last_name", "full_name",
        ],
        "dim_customer": [
            "customer_id", "first_name", "last_name", "full_name",
        ],
        "dim_track": [
            "track_id", "track_name", "milliseconds",
            "duration_seconds", "duration_minutes", "bytes",
            "unit_price", "playlist_count",
        ],
        "fact_sales": [
            "date_key", "customer_key", "track_key", "employee_key",
            "invoice_id", "invoice_line_id", "unit_price",
            "quantity", "total_amount",
        ],
    }    

    columnas_unicas = {
        "dim_date": ["full_date"],
        "dim_employee": ["employee_id"],
        "dim_customer": ["customer_id"],
        "dim_track": ["track_id"],
        "fact_sales": ["invoice_line_id"],
    }

    limites_texto = {
        "dim_date": {
            "month_name": 20,
            "day_name": 20,
        },
        "dim_employee": {
            "first_name": 50,
            "last_name": 50,
            "full_name": 100,
            "title": 60,
            "reports_to_name": 100,
            "address": 100,
            "city": 50,
            "state": 50,
            "country": 50,
            "postal_code": 20,
            "phone": 30,
            "email": 100,
        },
        "dim_customer": {
            "first_name": 50,
            "last_name": 50,
            "full_name": 100,
            "company": 80,
            "address": 100,
            "city": 50,
            "state": 50,
            "country": 50,
            "postal_code": 20,
            "phone": 30,
            "email": 100,
        },
        "dim_track": {
            "track_name": 200,
            "album_title": 160,
            "artist_name": 120,
            "media_type_name": 120,
            "genre_name": 120,
            "composer": 220,
        },
    }

    columnas_enteras = {
        "dim_date": [
            "year", "quarter", "month", "day", "day_of_week",
        ],
        "dim_employee": ["employee_id"],
        "dim_customer": ["customer_id"],
        "dim_track": [
            "track_id", "milliseconds", "bytes", "playlist_count",
        ],
        "fact_sales": [
            "date_key", "customer_key", "track_key", "employee_key",
            "invoice_id", "invoice_line_id", "quantity",
        ],
    }

    tablas_recibidas = set(data_dict.keys())
    tablas_faltantes = tablas_esperadas - tablas_recibidas


    if tablas_faltantes:
        raise ValueError("Faltan tablas esperadas en el diccionario de datos:" + ', '.join(sorted(tablas_faltantes)))

    for tabla in sorted(tablas_esperadas):
        print(f"Revisando tabla: {tabla}...")
        df = data_dict[tabla]

        if not isinstance(df, pd.DataFrame):
            raise TypeError(f"El valor asociado a la tabla '{tabla}' no es un DataFrame de pandas.")
        
        if df.empty:
            raise ValueError(f"El DataFrame para la tabla '{tabla}' está vacío.")

        clave = claves_primarias[tabla]

        if clave not in df.columns:
            raise ValueError(f"La columna de clave primaria '{clave}' no se encuentra en el DataFrame de la tabla '{tabla}'.")
        
        if df[clave].isna().any():
            raise ValueError(f"La columna de clave primaria '{clave}' en la tabla '{tabla}' contiene valores nulos.")
        
        if df[clave].duplicated().any():
            raise ValueError(f"La columna de clave primaria '{clave}' en la tabla '{tabla}' contiene valores duplicados.")
        
        if not pd.api.types.is_integer_dtype(df[clave].dtype):
            raise TypeError(
                f"{tabla}: la clave primaria '{clave}' "
                "debe tener un tipo de datos entero."
            )

        bits_clave = 64 if tabla == "fact_sales" else 32
        minimo_clave = -(2 ** (bits_clave - 1))
        maximo_clave = 2 ** (bits_clave - 1) - 1

        if not df[clave].between(minimo_clave, maximo_clave).all():
            raise ValueError(
                f"{tabla}: la clave primaria '{clave}' contiene "
                f"valores fuera del rango de {bits_clave} bits."
            )


        for columna in columnas_obligatorias[tabla]:
            if columna not in df.columns:
                raise ValueError(f"La columna obligatoria '{columna}' no se encuentra en el DataFrame de la tabla '{tabla}'.")
            
            if df[columna].isna().any():
                raise ValueError(f"La columna obligatoria '{columna}' en la tabla '{tabla}' contiene valores nulos.")

        for columna in columnas_unicas[tabla]:
            if df[columna].duplicated().any():
                raise ValueError(f"La columna '{columna}' en la tabla '{tabla}' contiene valores duplicados, pero debería ser única.")

        for columna, limite in limites_texto.get(tabla, {}).items():
            if columna not in df.columns:
                raise ValueError(
                    f"{tabla}: falta la columna de texto '{columna}'."
                )

            valores = df[columna].dropna()

            if not valores.map(lambda valor: isinstance(valor, str)).all():
                raise TypeError(
                    f"{tabla}: '{columna}' debe contener texto."
                )

            if valores.str.len().gt(limite).any():
                raise ValueError(
                    f"{tabla}: '{columna}' supera el límite "
                    f"de {limite} caracteres."
                )
            
        for columna in columnas_enteras[tabla]:
            if not pd.api.types.is_integer_dtype(df[columna].dtype):
                raise TypeError(
                    f"{tabla}: '{columna}' debe tener un tipo entero."
                )

            es_bigint = tabla == "dim_track" and columna == "bytes"
            bits = 64 if es_bigint else 32

            minimo = -(2 ** (bits - 1))
            maximo = 2 ** (bits - 1) - 1

            if not df[columna].between(minimo, maximo).all():
                raise ValueError(
                    f"{tabla}: '{columna}' contiene valores "
                    f"fuera del rango de un entero de {bits} bits."
                )
           

        print(f"  {tabla}: comprobaciones actuales superadas ({len(df)} filas).")

    print("Verificando relaciones entre ventas y dimensiones...")
    relaciones = {
        "date_key": "dim_date",
        "customer_key": "dim_customer",
        "track_key": "dim_track",
        "employee_key": "dim_employee",
    }

    ventas = data_dict["fact_sales"]

    for columna, dimension in relaciones.items():
        claves_validas = data_dict[dimension][columna]
        referencias_invalidas = ~ventas[columna].isin(claves_validas)
        if referencias_invalidas.any():
            ejemplos = (ventas.loc[referencias_invalidas, columna].drop_duplicates().head(5).tolist())
            raise ValueError(f"Se encontraron referencias inválidas en la columna '{columna}' de 'fact_sales' que no existen en la dimensión '{dimension}': {ejemplos}")

        print(f"  fact_sales.{columna} -> {dimension}: referencias válidas.")

    print("Validación del modelo DW completada sin errores en las reglas implementadas.")
