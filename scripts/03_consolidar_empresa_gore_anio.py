from pathlib import Path
import pandas as pd


# ============================================================
# 1. RUTAS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
INSUMOS_DIR = DATA_DIR / "insumos_originales"
INTERMEDIATE_DIR = DATA_DIR / "bases_intermedias"

ARCHIVO_EMPRESAS = (
    INTERMEDIATE_DIR / "empresas_2021_2022_2024.csv"
)

ARCHIVO_EMPRESA_GORE = (
    INTERMEDIATE_DIR / "empresa_gore_anio_base.csv"
)

ARCHIVO_CONTRATOS_LARGO = (
    INTERMEDIATE_DIR / "contrataciones_largo_2021_2022_2024.csv"
)

ARCHIVO_CONTRATACIONES_COMPLETO = (
    INSUMOS_DIR / "contrataciones_2004_2024.csv"
)

SALIDA = (
    INTERMEDIATE_DIR / "empresa_gore_anio_pre_inco.csv"
)


# ============================================================
# 2. CONFIGURACIÓN
# ============================================================

COLUMNAS_EMPRESA = [
    "EMPRESA_1",
    "EMPRESA_2",
    "EMPRESA_3",
    "EMPRESA_4",
    "EMPRESA_5",
    "EMPRESA_6",
    "EMPRESA_7",
    "EMPRESA_8",
    "EMPRESA_9"
]


# ============================================================
# 3. FUNCIONES AUXILIARES
# ============================================================

def limpiar_ruc(valor):
    """
    Convierte RUC a texto y limpia espacios y '.0'.
    """
    if pd.isna(valor):
        return pd.NA

    ruc = str(valor).strip()

    if ruc.endswith(".0"):
        ruc = ruc[:-2]

    if ruc == "":
        return pd.NA

    return ruc


def leer_csv_seguro(ruta, dtype=None):
    """
    Intenta leer un CSV usando varias codificaciones.
    """
    codificaciones = [
        "utf-8-sig",
        "utf-8",
        "latin1",
        "cp1252"
    ]

    ultimo_error = None

    for encoding in codificaciones:

        try:

            df = pd.read_csv(
                ruta,
                encoding=encoding,
                dtype=dtype,
                low_memory=False
            )

            return df

        except UnicodeDecodeError as error:

            ultimo_error = error

    raise ultimo_error


def tabla_nulos(df):
    """
    Genera una tabla con número y porcentaje de NA.
    """
    return pd.DataFrame({
        "variable": df.columns,
        "n_na": [
            df[col].isna().sum()
            for col in df.columns
        ],
        "porcentaje_na": [
            round(
                df[col].isna().mean() * 100,
                2
            )
            for col in df.columns
        ]
    })


# ============================================================
# 4. CARGAR BASE EMPRESARIAL
# ============================================================

empresas = leer_csv_seguro(
    ARCHIVO_EMPRESAS,
    dtype={
        "ruc": str
    }
)


empresas["ruc"] = (
    empresas["ruc"]
    .apply(limpiar_ruc)
)


if empresas["ruc"].duplicated().any():

    raise ValueError(
        "ERROR: empresas_2021_2022_2024.csv "
        "contiene RUC duplicados."
    )


print("\n" + "=" * 78)
print("BASE EMPRESARIAL")
print("=" * 78)

print(
    f"Empresas: "
    f"{len(empresas):,}"
)


# ============================================================
# 5. CARGAR BASE EMPRESA-GORE-AÑO
# ============================================================

empresa_gore = leer_csv_seguro(
    ARCHIVO_EMPRESA_GORE,
    dtype={
        "ruc": str,
        "gore": str
    }
)


empresa_gore["ruc"] = (
    empresa_gore["ruc"]
    .apply(limpiar_ruc)
)


empresa_gore["anio"] = pd.to_numeric(
    empresa_gore["anio"],
    errors="coerce"
).astype("Int64")


duplicados_empresa_gore = (
    empresa_gore
    .duplicated(
        subset=[
            "ruc",
            "anio",
            "gore"
        ]
    )
    .sum()
)


if duplicados_empresa_gore > 0:

    raise ValueError(
        "ERROR: empresa_gore_anio_base.csv tiene "
        "duplicados ruc + anio + gore."
    )


print("\n" + "=" * 78)
print("BASE EMPRESA-GORE-AÑO")
print("=" * 78)

print(
    f"Filas empresa-GORE-año: "
    f"{len(empresa_gore):,}"
)

print(
    f"RUC distintos: "
    f"{empresa_gore['ruc'].nunique():,}"
)


# ============================================================
# 6. CARGAR CONTRATACIONES LARGAS 2021/2022/2024
# ============================================================

contratos_largo = leer_csv_seguro(
    ARCHIVO_CONTRATOS_LARGO,
    dtype={
        "ruc": str,
        "gore": str
    }
)


contratos_largo["ruc"] = (
    contratos_largo["ruc"]
    .apply(limpiar_ruc)
)


contratos_largo["anio"] = pd.to_numeric(
    contratos_largo["anio"],
    errors="coerce"
).astype("Int64")


contratos_largo["monto_contrato"] = pd.to_numeric(
    contratos_largo["monto_contrato"],
    errors="coerce"
)


# ============================================================
# 7. UNIR CMC A CADA CONTRATO
# ============================================================

cmc_empresas = empresas[
    [
        "ruc",
        "cmc"
    ]
].copy()


cmc_empresas["cmc"] = pd.to_numeric(
    cmc_empresas["cmc"],
    errors="coerce"
)


contratos_cmc = contratos_largo.merge(
    cmc_empresas,
    on="ruc",
    how="left",
    validate="many_to_one"
)


# ============================================================
# 8. CALCULAR SUPERACIÓN DEL CMC
# ============================================================

# Solo se puede evaluar cuando existen:
# - monto_contrato
# - cmc

contratos_cmc["supera_cmc"] = pd.NA


mask_evaluable = (
    contratos_cmc["monto_contrato"].notna()
    & contratos_cmc["cmc"].notna()
)


contratos_cmc.loc[
    mask_evaluable,
    "supera_cmc"
] = (
    contratos_cmc.loc[
        mask_evaluable,
        "monto_contrato"
    ]
    >
    contratos_cmc.loc[
        mask_evaluable,
        "cmc"
    ]
).astype(int)


contratos_cmc["supera_cmc"] = (
    contratos_cmc["supera_cmc"]
    .astype("Int64")
)


print("\n" + "=" * 78)
print("EVALUACIÓN CMC A NIVEL CONTRATO")
print("=" * 78)

print(
    f"Filas empresa-contrato: "
    f"{len(contratos_cmc):,}"
)

print(
    f"Contratos evaluables por CMC: "
    f"{contratos_cmc['supera_cmc'].notna().sum():,}"
)

print(
    f"Contratos no evaluables por CMC: "
    f"{contratos_cmc['supera_cmc'].isna().sum():,}"
)

print(
    f"Casos que superan CMC: "
    f"{(contratos_cmc['supera_cmc'] == 1).sum():,}"
)


# ============================================================
# 9. AGREGAR CMC POR EMPRESA-GORE-AÑO
# ============================================================

cmc_gore_anio = (
    contratos_cmc
    .groupby(
        [
            "ruc",
            "anio",
            "gore"
        ],
        as_index=False
    )
    .agg(
        n_contratos_cmc_evaluables=(
            "supera_cmc",
            "count"
        ),
        n_supera_cmc=(
            "supera_cmc",
            "sum"
        )
    )
)


cmc_gore_anio["n_contratos_cmc_evaluables"] = (
    cmc_gore_anio["n_contratos_cmc_evaluables"]
    .astype("Int64")
)


cmc_gore_anio["n_supera_cmc"] = (
    cmc_gore_anio["n_supera_cmc"]
    .astype("Int64")
)


# Si ningún contrato es evaluable, no podemos afirmar
# que n_supera_cmc = 0.
cmc_gore_anio.loc[
    cmc_gore_anio["n_contratos_cmc_evaluables"] == 0,
    "n_supera_cmc"
] = pd.NA


cmc_gore_anio["prop_supera_cmc"] = (
    cmc_gore_anio["n_supera_cmc"]
    /
    cmc_gore_anio["n_contratos_cmc_evaluables"]
)


cmc_gore_anio.loc[
    cmc_gore_anio["n_contratos_cmc_evaluables"] == 0,
    "prop_supera_cmc"
] = pd.NA


# ============================================================
# 10. UNIR VARIABLES CMC A EMPRESA-GORE-AÑO
# ============================================================

empresa_gore = empresa_gore.merge(
    cmc_gore_anio,
    on=[
        "ruc",
        "anio",
        "gore"
    ],
    how="left",
    validate="one_to_one"
)


# ============================================================
# 11. OBTENER PRIMER AÑO DE CONTRATACIÓN 2004-2024
# ============================================================

contratos_total = leer_csv_seguro(
    ARCHIVO_CONTRATACIONES_COMPLETO,
    dtype=str
)


if "FECHA" not in contratos_total.columns:

    raise ValueError(
        "No se encontró la columna FECHA "
        "en contrataciones_2004_2024.csv"
    )


contratos_total["fecha"] = pd.to_datetime(
    contratos_total["FECHA"],
    format="%d/%m/%Y",
    errors="coerce"
)


contratos_total["anio"] = (
    contratos_total["fecha"]
    .dt.year
    .astype("Int64")
)


# Pasamos EMPRESA_1 ... EMPRESA_9 a formato largo,
# pero aquí solo necesitamos RUC + año.

historial_largo = contratos_total.melt(
    id_vars=[
        "anio"
    ],
    value_vars=COLUMNAS_EMPRESA,
    value_name="ruc"
)


historial_largo["ruc"] = (
    historial_largo["ruc"]
    .apply(limpiar_ruc)
)


historial_largo = historial_largo[
    historial_largo["ruc"].notna()
    & historial_largo["anio"].notna()
].copy()


# Evitar repeticiones innecesarias del mismo RUC/año
historial_largo = historial_largo[
    [
        "ruc",
        "anio"
    ]
].drop_duplicates()


primer_contrato = (
    historial_largo
    .groupby(
        "ruc",
        as_index=False
    )
    .agg(
        primer_anio_contratacion=(
            "anio",
            "min"
        )
    )
)


primer_contrato["primer_anio_contratacion"] = (
    primer_contrato["primer_anio_contratacion"]
    .astype("Int64")
)


# ============================================================
# 12. UNIR PRIMER AÑO DE CONTRATACIÓN
# ============================================================

empresa_gore = empresa_gore.merge(
    primer_contrato,
    on="ruc",
    how="left",
    validate="many_to_one"
)


# ============================================================
# 13. CALCULAR EXPERIENCIA EN CONTRATACIÓN PÚBLICA
# ============================================================

empresa_gore["experiencia_contratacion"] = (
    empresa_gore["anio"]
    -
    empresa_gore["primer_anio_contratacion"]
)


empresa_gore["experiencia_contratacion"] = (
    empresa_gore["experiencia_contratacion"]
    .astype("Int64")
)


# ============================================================
# 14. UNIR ATRIBUTOS EMPRESARIALES
# ============================================================

empresa_gore = empresa_gore.merge(
    empresas,
    on="ruc",
    how="left",
    validate="many_to_one"
)


# ============================================================
# 15. PREPARAR FECHA DE INICIO DE ACTIVIDADES
# ============================================================

empresa_gore["fecha_inicio_actividades_dt"] = pd.to_datetime(
    empresa_gore["fecha_inicio_actividades"],
    format="%d/%m/%Y",
    errors="coerce"
)


empresa_gore["anio_inicio_actividades"] = (
    empresa_gore["fecha_inicio_actividades_dt"]
    .dt.year
    .astype("Int64")
)


# ============================================================
# 16. CALCULAR ANTIGÜEDAD DE LA EMPRESA
# ============================================================

empresa_gore["antiguedad_empresa"] = (
    empresa_gore["anio"]
    -
    empresa_gore["anio_inicio_actividades"]
)


empresa_gore["antiguedad_empresa"] = (
    empresa_gore["antiguedad_empresa"]
    .astype("Int64")
)


# ============================================================
# 17. IDENTIFICAR INCONSISTENCIAS TEMPORALES
# ============================================================

# Si SUNAT dice que la empresa inició actividades después del año
# en que aparece contratando, no corregimos el dato silenciosamente.
# Lo marcamos para revisión.

empresa_gore["inicio_posterior_contratacion"] = (
    (
        empresa_gore["antiguedad_empresa"].notna()
        &
        (empresa_gore["antiguedad_empresa"] < 0)
    )
    .astype(int)
)


# Para análisis no queremos antigüedades negativas.
# Se convierten en NA, pero queda el indicador anterior.

empresa_gore.loc[
    empresa_gore["antiguedad_empresa"] < 0,
    "antiguedad_empresa"
] = pd.NA


empresa_gore["inicio_posterior_contratacion"] = (
    empresa_gore["inicio_posterior_contratacion"]
    .astype("Int64")
)


# ============================================================
# 18. VALIDAR NÚMERO DE CONTRATOS
# ============================================================

# Comparamos n_contratos de empresa_gore_anio_base
# contra el conteo directamente obtenido de contratos_largo.

control_contratos = (
    contratos_largo
    .groupby(
        [
            "ruc",
            "anio",
            "gore"
        ],
        as_index=False
    )
    .agg(
        n_contratos_control=(
            "id_contrato",
            "nunique"
        )
    )
)


control = empresa_gore[
    [
        "ruc",
        "anio",
        "gore",
        "n_contratos"
    ]
].merge(
    control_contratos,
    on=[
        "ruc",
        "anio",
        "gore"
    ],
    how="left",
    validate="one_to_one"
)


control["diferencia"] = (
    control["n_contratos"]
    -
    control["n_contratos_control"]
)


n_diferencias = (
    (control["diferencia"] != 0)
    .sum()
)


print("\n" + "=" * 78)
print("CONTROL DE NÚMERO DE CONTRATOS")
print("=" * 78)

print(
    f"Filas con diferencia en n_contratos: "
    f"{n_diferencias:,}"
)


if n_diferencias > 0:

    raise ValueError(
        "ERROR: el número de contratos no coincide "
        "entre las bases."
    )


# ============================================================
# 19. ELIMINAR VARIABLE TEMPORAL AUXILIAR
# ============================================================

empresa_gore = empresa_gore.drop(
    columns=[
        "fecha_inicio_actividades_dt"
    ]
)


# ============================================================
# 20. TIPOS DE DATOS
# ============================================================

columnas_enteras = [
    "anio",
    "n_contratos",
    "n_gores_anio",
    "n_contratos_cmc_evaluables",
    "n_supera_cmc",
    "primer_anio_contratacion",
    "experiencia_contratacion",
    "anio_inicio_actividades",
    "antiguedad_empresa",
    "inicio_posterior_contratacion",
    "cantidad_rubros",
    "sanciones_tcp_acum",
    "penalidades_acum",
    "inhabilitacion_judicial",
    "inhabilitacion_administrativa",
    "sunat_ok",
    "tiene_info_sunat",
    "tiene_info_proveedores_estado"
]


for columna in columnas_enteras:

    if columna in empresa_gore.columns:

        empresa_gore[columna] = pd.to_numeric(
            empresa_gore[columna],
            errors="coerce"
        ).astype("Int64")


empresa_gore["cmc"] = pd.to_numeric(
    empresa_gore["cmc"],
    errors="coerce"
)


empresa_gore["prop_supera_cmc"] = pd.to_numeric(
    empresa_gore["prop_supera_cmc"],
    errors="coerce"
)


# ============================================================
# 21. ORDEN FINAL DE VARIABLES
# ============================================================

orden_columnas = [
    # Identificación
    "ruc",
    "razon_social",
    "nombre_comercial",

    # Dimensión temporal y territorial
    "anio",
    "gore",

    # Trayectoria
    "fecha_inscripcion",
    "fecha_inicio_actividades",
    "anio_inicio_actividades",
    "antiguedad_empresa",
    "inicio_posterior_contratacion",

    "primer_anio_contratacion",
    "experiencia_contratacion",

    # Contrataciones
    "n_contratos",
    "n_gores_anio",

    # CMC
    "cmc",
    "n_contratos_cmc_evaluables",
    "n_supera_cmc",
    "prop_supera_cmc",

    # Perfil empresarial
    "tipo_contribuyente",
    "estado",
    "condicion",
    "fecha_baja",
    "domicilio",

    # Actividades económicas
    "actividad_principal",
    "cantidad_rubros",
    "actividades_economicas",

    # Antecedentes
    "sanciones_tcp_acum",
    "penalidades_acum",
    "inhabilitacion_judicial",
    "inhabilitacion_administrativa",

    # Control de fuente
    "fecha_consulta_sunat",
    "sunat_ok",
    "tiene_info_sunat",
    "tiene_info_proveedores_estado"
]


# Solo conserva columnas que efectivamente existan.
orden_columnas = [
    col
    for col in orden_columnas
    if col in empresa_gore.columns
]


empresa_gore = empresa_gore[
    orden_columnas
].copy()


# ============================================================
# 22. VALIDACIÓN DE DUPLICADOS
# ============================================================

duplicados_finales = (
    empresa_gore
    .duplicated(
        subset=[
            "ruc",
            "anio",
            "gore"
        ]
    )
    .sum()
)


if duplicados_finales > 0:

    raise ValueError(
        "ERROR: la base final contiene duplicados "
        "ruc + anio + gore."
    )


# ============================================================
# 23. RESUMEN DE NULOS
# ============================================================

nulos = tabla_nulos(
    empresa_gore
)


print("\n" + "=" * 78)
print("VALORES FALTANTES POR VARIABLE")
print("=" * 78)

print(
    nulos.to_string(
        index=False
    )
)


# ============================================================
# 24. RESUMEN FINAL
# ============================================================

print("\n" + "=" * 78)
print("RESUMEN BASE EMPRESA-GORE-AÑO PRE-INCO")
print("=" * 78)

print(
    f"Filas finales                       : "
    f"{len(empresa_gore):,}"
)

print(
    f"RUC distintos                       : "
    f"{empresa_gore['ruc'].nunique():,}"
)

print(
    f"Duplicados RUC-año-GORE             : "
    f"{duplicados_finales:,}"
)

print(
    f"Filas con CMC                       : "
    f"{empresa_gore['cmc'].notna().sum():,}"
)

print(
    f"Filas sin CMC                       : "
    f"{empresa_gore['cmc'].isna().sum():,}"
)

print(
    f"Filas con n_supera_cmc calculable   : "
    f"{empresa_gore['n_supera_cmc'].notna().sum():,}"
)

print(
    f"Filas sin n_supera_cmc calculable   : "
    f"{empresa_gore['n_supera_cmc'].isna().sum():,}"
)

print(
    f"Casos empresa-GORE-año con >=1 "
    f"superación CMC                      : "
    f"{(empresa_gore['n_supera_cmc'] > 0).sum():,}"
)

print(
    f"Filas con inicio posterior al "
    f"año de contratación                : "
    f"{empresa_gore['inicio_posterior_contratacion'].sum():,}"
)

print(
    f"Sin antigüedad calculable            : "
    f"{empresa_gore['antiguedad_empresa'].isna().sum():,}"
)

print(
    f"Sin experiencia contractual          : "
    f"{empresa_gore['experiencia_contratacion'].isna().sum():,}"
)


# ============================================================
# 25. DISTRIBUCIÓN POR AÑO
# ============================================================

print("\n" + "=" * 78)
print("OBSERVACIONES POR AÑO")
print("=" * 78)

print(
    empresa_gore["anio"]
    .value_counts()
    .sort_index()
    .to_string()
)


# ============================================================
# 26. GUARDAR
# ============================================================

empresa_gore.to_csv(
    SALIDA,
    index=False,
    encoding="utf-8-sig"
)


print("\n" + "=" * 78)
print("ARCHIVO GENERADO CORRECTAMENTE")
print("=" * 78)

print(
    f"\n{SALIDA}"
)

print(
    f"\nDimensiones: "
    f"{len(empresa_gore):,} filas x "
    f"{len(empresa_gore.columns):,} columnas"
)

print(
    "\nUnidad de observación: RUC × GORE × año."
)