import pandas as pd 

def validar_modelo_dw(data_dict: dict) -> None:
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

    tablas_recibidas = set(data_dict.keys())
    tablas_faltantes = tablas_esperadas - tablas_recibidas


    if tablas_faltantes:
        raise ValueError("Faltan tablas esperadas en el diccionario de datos:" + ', '.join(sorted(tablas_faltantes)))

    for tabla in sorted(tablas_esperadas):
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

        for columna in columnas_obligatorias[tabla]:
            if columna not in df.columns:
                raise ValueError(f"La columna obligatoria '{columna}' no se encuentra en el DataFrame de la tabla '{tabla}'.")
            
            if df[columna].isna().any():
                raise ValueError(f"La columna obligatoria '{columna}' en la tabla '{tabla}' contiene valores nulos.")

        for columna in columnas_unicas[tabla]:
            if df[columna].duplicated().any():
                raise ValueError(f"La columna '{columna}' en la tabla '{tabla}' contiene valores duplicados, pero debería ser única.")

           

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