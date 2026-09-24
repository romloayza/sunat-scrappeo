from pathlib import Path
import json
import pandas as pd


# ============================================================
# 1. RUTAS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
INSUMOS_DIR = DATA_DIR / "insumos_originales"
INTERMEDIATE_DIR = DATA_DIR / "bases_intermedias"

ARCHIVO_RUCS = INSUMOS_DIR / "rucs_2021_2022_2024.json"
ARCHIVO_SUNAT = INSUMOS_DIR / "sunat_rucs_2021_2022_2024.json"
ARCHIVO_PROVEEDORES = INSUMOS_DIR / "proveedores_estado_info.xlsx"

SALIDA = INTERMEDIATE_DIR / "empresas_2021_2022_2024.csv"


# ============================================================
# 2. FUNCIONES AUXILIARES
# ============================================================

def limpiar_ruc(valor):
    """
    Convierte el RUC a texto y elimina espacios o '.0'
    que puedan provenir de Excel.
    """
    if pd.isna(valor):
        return pd.NA

    ruc = str(valor).strip()

    if ruc.endswith(".0"):
        ruc = ruc[:-2]

    return ruc


def normalizar_para_comparar(valor):
    """
    Normaliza texto únicamente para comparar entre fuentes.
    No modifica el valor que irá a la base final.
    """
    if pd.isna(valor):
        return pd.NA

    texto = str(valor).strip()

    if texto == "":
        return pd.NA

    return texto.upper()


def extraer_actividad_principal(actividades):
    """
    Extrae la actividad económica marcada como Principal.
    """
    if not isinstance(actividades, list):
        return pd.NA

    actividades_limpias = [
        str(x).strip()
        for x in actividades
        if x is not None and str(x).strip()
    ]

    if len(actividades_limpias) == 0:
        return pd.NA

    for actividad in actividades_limpias:
        if actividad.lower().startswith("principal"):
            return actividad

    return actividades_limpias[0]


def contar_rubros(actividades):
    """
    Cuenta la cantidad de actividades económicas registradas
    por SUNAT.
    """
    if not isinstance(actividades, list):
        return pd.NA

    actividades_limpias = [
        str(x).strip()
        for x in actividades
        if x is not None and str(x).strip()
    ]

    if len(actividades_limpias) == 0:
        return pd.NA

    return len(actividades_limpias)


def actividades_a_texto(actividades):
    """
    Convierte la lista de actividades económicas en texto
    para guardarla en el CSV.
    """
    if not isinstance(actividades, list):
        return pd.NA

    actividades_limpias = [
        str(x).strip()
        for x in actividades
        if x is not None and str(x).strip()
    ]

    if len(actividades_limpias) == 0:
        return pd.NA

    return " | ".join(actividades_limpias)


def verificar_ruc_unico(df, nombre_fuente):
    """
    Verifica que exista como máximo una fila por RUC.
    Si encuentra duplicados, detiene el proceso.
    """
    duplicados = df[
        df["ruc"].duplicated(keep=False)
    ].copy()

    if not duplicados.empty:

        print("\n" + "=" * 75)
        print(f"ERROR: RUC DUPLICADOS EN {nombre_fuente.upper()}")
        print("=" * 75)

        conteo = (
            duplicados["ruc"]
            .value_counts()
            .sort_values(ascending=False)
        )

        print(conteo.head(30).to_string())

        raise ValueError(
            f"La fuente '{nombre_fuente}' contiene RUC duplicados. "
            "El proceso se detuvo para evitar multiplicar observaciones."
        )


def contar_discrepancias(df, columna_1, columna_2):
    """
    Cuenta discrepancias solo cuando ambas fuentes tienen información.
    """
    validos = (
        df[columna_1].notna()
        & df[columna_2].notna()
    )

    return (
        df.loc[validos, columna_1]
        != df.loc[validos, columna_2]
    ).sum()


# ============================================================
# 3. CARGAR LISTA MAESTRA DE RUC
# ============================================================

with open(
    ARCHIVO_RUCS,
    "r",
    encoding="utf-8-sig"
) as f:

    lista_rucs = json.load(f)


lista_rucs = [
    limpiar_ruc(ruc)
    for ruc in lista_rucs
    if ruc is not None
]


# Eliminar duplicados manteniendo el orden original
lista_rucs_unicos = list(
    dict.fromkeys(lista_rucs)
)


print("\n" + "=" * 75)
print("LISTA MAESTRA DE RUC")
print("=" * 75)

print(
    f"RUC en archivo original : "
    f"{len(lista_rucs):,}"
)

print(
    f"RUC únicos              : "
    f"{len(lista_rucs_unicos):,}"
)

print(
    f"Duplicados eliminados   : "
    f"{len(lista_rucs) - len(lista_rucs_unicos):,}"
)


# Base que manda sobre todo el proceso
empresas = pd.DataFrame({
    "ruc": lista_rucs_unicos
})


# ============================================================
# 4. CARGAR DATOS SUNAT
# ============================================================

with open(
    ARCHIVO_SUNAT,
    "r",
    encoding="utf-8-sig"
) as f:

    datos_sunat = json.load(f)


sunat = pd.DataFrame(datos_sunat)


# Asegurar que exista la columna RUC
if "ruc" not in sunat.columns:
    raise ValueError(
        "El JSON de SUNAT no contiene una columna 'ruc'."
    )


sunat["ruc"] = (
    sunat["ruc"]
    .apply(limpiar_ruc)
)


# Verificar duplicados
verificar_ruc_unico(
    sunat,
    "SUNAT"
)


# ============================================================
# 5. CREAR VARIABLES DERIVADAS DE SUNAT
# ============================================================

# Si algún registro no tuviera actividades_economicas,
# creamos la columna vacía para evitar errores.
if "actividades_economicas" not in sunat.columns:
    sunat["actividades_economicas"] = pd.NA


sunat["actividad_principal"] = (
    sunat["actividades_economicas"]
    .apply(extraer_actividad_principal)
)


sunat["cantidad_rubros"] = (
    sunat["actividades_economicas"]
    .apply(contar_rubros)
)


sunat["actividades_economicas_texto"] = (
    sunat["actividades_economicas"]
    .apply(actividades_a_texto)
)


# ============================================================
# 6. SELECCIONAR VARIABLES SUNAT
# ============================================================

columnas_sunat = [
    "ruc",
    "razon_social",
    "nombre_comercial",
    "fecha_inscripcion",
    "fecha_inicio_actividades",
    "tipo_contribuyente",
    "estado_contribuyente",
    "condicion_contribuyente",
    "fecha_baja",
    "actividad_principal",
    "cantidad_rubros",
    "actividades_economicas_texto",
    "fecha_consulta",
    "ok"
]


# reindex permite que, si falta alguna variable en algún JSON,
# se cree como NA en vez de generar un error.
sunat = sunat.reindex(
    columns=columnas_sunat
).copy()


sunat = sunat.rename(columns={
    "estado_contribuyente": "estado",
    "condicion_contribuyente": "condicion",
    "actividades_economicas_texto": "actividades_economicas",
    "fecha_consulta": "fecha_consulta_sunat",
    "ok": "sunat_ok"
})


# ============================================================
# 7. CARGAR PROVEEDORES DEL ESTADO
# ============================================================

proveedores = pd.read_excel(
    ARCHIVO_PROVEEDORES,
    dtype={
        "ruc": str
    }
)


if "ruc" not in proveedores.columns:
    raise ValueError(
        "proveedores_estado_info.xlsx no contiene una columna 'ruc'."
    )


proveedores["ruc"] = (
    proveedores["ruc"]
    .apply(limpiar_ruc)
)


# Verificar duplicados
verificar_ruc_unico(
    proveedores,
    "proveedores_estado"
)


# ============================================================
# 8. COMPARAR VARIABLES REPETIDAS ENTRE FUENTES
# ============================================================

# SUNAT será la fuente final para:
# - tipo_contribuyente
# - estado
# - condicion
#
# Pero antes comprobamos cuántas diferencias existen con
# proveedores_estado_info.xlsx.


columnas_comparacion_estado = [
    "ruc",
    "tipoContribuyente",
    "estado",
    "condicion"
]


proveedores_comparacion = (
    proveedores
    .reindex(columns=columnas_comparacion_estado)
    .copy()
)


proveedores_comparacion = (
    proveedores_comparacion
    .rename(columns={
        "tipoContribuyente": "tipo_contribuyente_estado",
        "estado": "estado_estado",
        "condicion": "condicion_estado"
    })
)


sunat_comparacion = (
    sunat[
        [
            "ruc",
            "tipo_contribuyente",
            "estado",
            "condicion"
        ]
    ]
    .copy()
)


sunat_comparacion = (
    sunat_comparacion
    .rename(columns={
        "tipo_contribuyente": "tipo_contribuyente_sunat",
        "estado": "estado_sunat",
        "condicion": "condicion_sunat"
    })
)


comparacion = sunat_comparacion.merge(
    proveedores_comparacion,
    on="ruc",
    how="inner",
    validate="one_to_one"
)


columnas_normalizar = [
    "tipo_contribuyente_sunat",
    "tipo_contribuyente_estado",
    "estado_sunat",
    "estado_estado",
    "condicion_sunat",
    "condicion_estado"
]


for columna in columnas_normalizar:

    comparacion[columna] = (
        comparacion[columna]
        .apply(normalizar_para_comparar)
    )


discrep_tipo = contar_discrepancias(
    comparacion,
    "tipo_contribuyente_sunat",
    "tipo_contribuyente_estado"
)


discrep_estado = contar_discrepancias(
    comparacion,
    "estado_sunat",
    "estado_estado"
)


discrep_condicion = contar_discrepancias(
    comparacion,
    "condicion_sunat",
    "condicion_estado"
)


print("\n" + "=" * 75)
print("COMPARACIÓN ENTRE SUNAT Y PROVEEDORES ESTADO")
print("=" * 75)

print(
    f"RUC presentes en ambas fuentes       : "
    f"{len(comparacion):,}"
)

print(
    f"Discrepancias tipo contribuyente     : "
    f"{discrep_tipo:,}"
)

print(
    f"Discrepancias estado                 : "
    f"{discrep_estado:,}"
)

print(
    f"Discrepancias condición              : "
    f"{discrep_condicion:,}"
)

print(
    "\nLa base final conservará únicamente "
    "tipo_contribuyente, estado y condicion de SUNAT."
)


# ============================================================
# 9. SELECCIONAR VARIABLES DE PROVEEDORES ESTADO
# ============================================================

# No incluimos:
# - tipoContribuyente
# - estado
# - condicion
#
# porque ya vienen de SUNAT.


columnas_proveedores = [
    "ruc",
    "domicilio",
    "cmc",
    "sancionesTcp",
    "penalidades",
    "inhabilitacionMandatoJudicial",
    "inhabilitacionAdministrativa"
]


proveedores_limpio = (
    proveedores
    .reindex(columns=columnas_proveedores)
    .copy()
)


proveedores_limpio = (
    proveedores_limpio
    .rename(columns={
        "sancionesTcp": "sanciones_tcp_acum",
        "penalidades": "penalidades_acum",
        "inhabilitacionMandatoJudicial":
            "inhabilitacion_judicial",
        "inhabilitacionAdministrativa":
            "inhabilitacion_administrativa"
    })
)


# ============================================================
# 10. CONTROL DE COBERTURA
# ============================================================

rucs_sunat = set(
    sunat["ruc"]
    .dropna()
)


rucs_proveedores = set(
    proveedores_limpio["ruc"]
    .dropna()
)


# ============================================================
# 11. MERGE CON SUNAT
# ============================================================

empresas = empresas.merge(
    sunat,
    on="ruc",
    how="left",
    validate="one_to_one"
)


# ============================================================
# 12. MERGE CON PROVEEDORES ESTADO
# ============================================================

empresas = empresas.merge(
    proveedores_limpio,
    on="ruc",
    how="left",
    validate="one_to_one"
)


# ============================================================
# 13. VARIABLES DE CONTROL DE COBERTURA
# ============================================================

empresas["tiene_info_sunat"] = (
    empresas["ruc"]
    .isin(rucs_sunat)
    .astype(int)
)


empresas["tiene_info_proveedores_estado"] = (
    empresas["ruc"]
    .isin(rucs_proveedores)
    .astype(int)
)


# Convertir sunat_ok a 1/0
empresas["sunat_ok"] = (
    empresas["sunat_ok"]
    .map({
        True: 1,
        False: 0
    })
    .astype("Int64")
)


# ============================================================
# 14. CONVERTIR VARIABLES NUMÉRICAS
# ============================================================

# CMC puede tener decimales, por eso se conserva como numérico decimal.
empresas["cmc"] = pd.to_numeric(
    empresas["cmc"],
    errors="coerce"
)


# Estas variables son conteos o indicadores y deben verse como enteros.
# Int64 permite conservar valores faltantes como <NA>.
columnas_enteras = [
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

    empresas[columna] = pd.to_numeric(
        empresas[columna],
        errors="coerce"
    ).astype("Int64")

    
# ============================================================
# 15. ORDEN FINAL DE LAS VARIABLES
# ============================================================

orden_columnas = [
    "ruc",

    "razon_social",
    "nombre_comercial",

    "fecha_inscripcion",
    "fecha_inicio_actividades",

    "tipo_contribuyente",
    "estado",
    "condicion",
    "fecha_baja",

    "domicilio",

    "actividad_principal",
    "cantidad_rubros",
    "actividades_economicas",

    "cmc",

    "sanciones_tcp_acum",
    "penalidades_acum",

    "inhabilitacion_judicial",
    "inhabilitacion_administrativa",

    "fecha_consulta_sunat",
    "sunat_ok",

    "tiene_info_sunat",
    "tiene_info_proveedores_estado"
]


empresas = empresas[
    orden_columnas
].copy()


# ============================================================
# 16. VALIDACIONES ESTRUCTURALES
# ============================================================

if not empresas["ruc"].is_unique:
    raise ValueError(
        "ERROR: la base final contiene RUC duplicados."
    )


if len(empresas) != len(lista_rucs_unicos):
    raise ValueError(
        "ERROR: se perdió o multiplicó algún RUC durante los merges."
    )


# ============================================================
# 17. TABLA DE VALORES FALTANTES
# ============================================================

tabla_nulos = pd.DataFrame({
    "variable": empresas.columns,
    "n_na": [
        empresas[columna].isna().sum()
        for columna in empresas.columns
    ],
    "porcentaje_na": [
        round(
            empresas[columna].isna().mean() * 100,
            2
        )
        for columna in empresas.columns
    ]
})


print("\n" + "=" * 75)
print("VALORES FALTANTES POR VARIABLE")
print("=" * 75)

print(
    tabla_nulos.to_string(
        index=False
    )
)


# ============================================================
# 18. RESUMEN DE CALIDAD
# ============================================================

print("\n" + "=" * 75)
print("RESUMEN DE CALIDAD DE LA BASE")
print("=" * 75)


print(
    f"Filas totales                         : "
    f"{len(empresas):,}"
)


print(
    f"RUC únicos                            : "
    f"{empresas['ruc'].nunique():,}"
)


print(
    f"RUC duplicados                        : "
    f"{empresas['ruc'].duplicated().sum():,}"
)


print(
    f"Con información SUNAT                 : "
    f"{empresas['tiene_info_sunat'].sum():,}"
)


print(
    f"Sin información SUNAT                 : "
    f"{(empresas['tiene_info_sunat'] == 0).sum():,}"
)


print(
    f"Con información proveedores Estado    : "
    f"{empresas['tiene_info_proveedores_estado'].sum():,}"
)


print(
    f"Sin información proveedores Estado    : "
    f"{(empresas['tiene_info_proveedores_estado'] == 0).sum():,}"
)


print(
    f"Con CMC disponible                    : "
    f"{empresas['cmc'].notna().sum():,}"
)


print(
    f"Sin CMC                               : "
    f"{empresas['cmc'].isna().sum():,}"
)


print(
    f"CMC igual a 0                         : "
    f"{(empresas['cmc'] == 0).sum():,}"
)


print(
    f"Con al menos 1 sanción TCP            : "
    f"{(empresas['sanciones_tcp_acum'] > 0).sum():,}"
)


print(
    f"Con al menos 1 penalidad              : "
    f"{(empresas['penalidades_acum'] > 0).sum():,}"
)


print(
    f"Con inhabilitación judicial           : "
    f"{(empresas['inhabilitacion_judicial'] > 0).sum():,}"
)


print(
    f"Con inhabilitación administrativa     : "
    f"{(empresas['inhabilitacion_administrativa'] > 0).sum():,}"
)


# ============================================================
# 19. GUARDAR CSV
# ============================================================

empresas.to_csv(
    SALIDA,
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 20. FINAL
# ============================================================

print("\n" + "=" * 75)
print("ARCHIVO GENERADO CORRECTAMENTE")
print("=" * 75)

print(
    f"\nArchivo:\n{SALIDA}"
)

print(
    f"\nDimensiones finales: "
    f"{len(empresas):,} filas x "
    f"{len(empresas.columns):,} columnas"
)

print(
    "\nCada RUC aparece exactamente una vez."
)