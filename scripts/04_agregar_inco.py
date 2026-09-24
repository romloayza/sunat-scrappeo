from pathlib import Path
import re
import unicodedata

import pandas as pd


# ============================================================
# 1. RUTAS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
INSUMOS_DIR = DATA_DIR / "insumos_originales"
INTERMEDIATE_DIR = DATA_DIR / "bases_intermedias"

ARCHIVO_PRE_INCO = (
    INTERMEDIATE_DIR / "empresa_gore_anio_pre_inco.csv"
)

ARCHIVO_INCO = (
    INSUMOS_DIR / "inco.XLSX"
)

SALIDA_INCO_LIMPIO = (
    INTERMEDIATE_DIR / "inco_gore_anio_limpio.csv"
)

SALIDA_FINAL = (
    DATA_DIR / "data_final_consolidada.csv"
)

SALIDA_SIN_INCO = (
    INTERMEDIATE_DIR / "control_empresa_gore_anio_sin_inco.csv"
)


# ============================================================
# 2. CONFIGURACIÓN
# ============================================================

ANIOS_INCO = [2021, 2022, 2024]


# ============================================================
# 3. FUNCIONES AUXILIARES
# ============================================================

def normalizar_texto(valor):
    """
    Normaliza texto para comparaciones y cruces:
    - mayúsculas
    - elimina tildes
    - elimina espacios repetidos
    """
    if pd.isna(valor):
        return pd.NA

    texto = str(valor).strip().upper()

    if texto == "":
        return pd.NA

    texto = unicodedata.normalize(
        "NFKD",
        texto
    )

    texto = "".join(
        caracter
        for caracter in texto
        if not unicodedata.combining(caracter)
    )

    texto = re.sub(
        r"\s+",
        " ",
        texto
    )

    return texto.strip()


def normalizar_nombre_columna(valor):
    """
    Normaliza nombres de columnas provenientes del Excel.
    """
    if pd.isna(valor):
        return ""

    texto = str(valor)

    texto = texto.replace("\n", " ")
    texto = texto.replace("\r", " ")

    texto = normalizar_texto(texto)

    if pd.isna(texto):
        return ""

    return texto


def leer_csv_seguro(ruta, dtype=None):
    """
    Lee CSV probando varias codificaciones.
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
            return pd.read_csv(
                ruta,
                encoding=encoding,
                dtype=dtype,
                low_memory=False
            )

        except UnicodeDecodeError as error:
            ultimo_error = error

    raise ultimo_error


def detectar_fila_encabezado(ruta_excel, hoja):
    """
    Busca automáticamente la fila que contiene los encabezados
    de cada hoja del INCO.
    """

    muestra = pd.read_excel(
        ruta_excel,
        sheet_name=hoja,
        header=None,
        nrows=20
    )

    for indice, fila in muestra.iterrows():

        valores = [
            normalizar_nombre_columna(valor)
            for valor in fila.tolist()
        ]

        tiene_departamento = (
            "DEPARTAMENTO" in valores
        )

        tiene_grupo = (
            "GRUPO_ENTIDAD" in valores
            or "GRUPO ENTIDAD" in valores
        )

        tiene_codigo = any(
            "COD CGR" == valor
            for valor in valores
        )

        if (
            tiene_departamento
            and tiene_grupo
            and tiene_codigo
        ):
            return indice

    raise ValueError(
        f"No se pudo detectar la fila de encabezados "
        f"en la hoja '{hoja}'."
    )


def buscar_columna(columnas, opciones):
    """
    Encuentra una columna normalizada entre varias alternativas.
    """

    for opcion in opciones:
        if opcion in columnas:
            return opcion

    raise ValueError(
        "No se encontró ninguna de estas columnas:\n"
        + "\n".join(opciones)
    )


def tabla_nulos(df):
    """
    Tabla de valores faltantes.
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
# 4. CARGAR BASE PRE-INCO
# ============================================================

base = leer_csv_seguro(
    ARCHIVO_PRE_INCO,
    dtype={
        "ruc": str,
        "gore": str
    }
)


base["anio"] = pd.to_numeric(
    base["anio"],
    errors="coerce"
).astype("Int64")


print("\n" + "=" * 78)
print("BASE EMPRESA-GORE-AÑO PRE-INCO")
print("=" * 78)

print(
    f"Filas: "
    f"{len(base):,}"
)

print(
    f"RUC distintos: "
    f"{base['ruc'].nunique():,}"
)

print(
    f"GORE distintos: "
    f"{base['gore'].nunique():,}"
)


# Validar unidad de observación
duplicados_base = (
    base
    .duplicated(
        subset=[
            "ruc",
            "anio",
            "gore"
        ]
    )
    .sum()
)


if duplicados_base > 0:

    raise ValueError(
        "ERROR: empresa_gore_anio_pre_inco.csv "
        "contiene duplicados RUC + año + GORE."
    )


# ============================================================
# 5. IDENTIFICAR HOJAS DEL INCO
# ============================================================

excel = pd.ExcelFile(
    ARCHIVO_INCO
)


print("\n" + "=" * 78)
print("HOJAS ENCONTRADAS EN INCO")
print("=" * 78)

for hoja in excel.sheet_names:
    print(f"- {hoja}")


hojas_por_anio = {}


for anio in ANIOS_INCO:

    coincidencias = [
        hoja
        for hoja in excel.sheet_names
        if str(anio) in normalizar_texto(hoja)
    ]

    if len(coincidencias) == 0:

        raise ValueError(
            f"No se encontró una hoja correspondiente a {anio}."
        )

    if len(coincidencias) > 1:

        raise ValueError(
            f"Se encontraron varias hojas para {anio}: "
            f"{coincidencias}"
        )

    hojas_por_anio[anio] = coincidencias[0]


# ============================================================
# 6. LIMPIAR CADA HOJA DEL INCO
# ============================================================

bases_inco = []


for anio, hoja in hojas_por_anio.items():

    print("\n" + "=" * 78)
    print(f"PROCESANDO INCO {anio}")
    print("=" * 78)

    fila_header = detectar_fila_encabezado(
        ARCHIVO_INCO,
        hoja
    )

    print(
        f"Hoja: {hoja}"
    )

    print(
        f"Fila de encabezado detectada: "
        f"{fila_header + 1}"
    )


    # --------------------------------------------------------
    # Leer hoja
    # --------------------------------------------------------

    df = pd.read_excel(
        ARCHIVO_INCO,
        sheet_name=hoja,
        header=fila_header
    )


    # --------------------------------------------------------
    # Normalizar nombres de columnas
    # --------------------------------------------------------

    df.columns = [
        normalizar_nombre_columna(col)
        for col in df.columns
    ]


    columnas = list(df.columns)


    # --------------------------------------------------------
    # Identificar columnas importantes
    # --------------------------------------------------------

    col_codigo = buscar_columna(
        columnas,
        [
            "COD CGR"
        ]
    )


    col_entidad = buscar_columna(
        columnas,
        [
            "ENTIDAD",
            "NOMBRE DE LA ENTIDAD"
        ]
    )


    col_departamento = buscar_columna(
        columnas,
        [
            "DEPARTAMENTO"
        ]
    )


    col_grupo = buscar_columna(
        columnas,
        [
            "GRUPO_ENTIDAD",
            "GRUPO ENTIDAD"
        ]
    )


    if anio in [2021, 2022]:

        col_puntaje = buscar_columna(
            columnas,
            [
                "PUNTAJE TOTAL"
            ]
        )

    elif anio == 2024:

        col_puntaje = buscar_columna(
            columnas,
            [
                "PUNTAJE INCO 2024",
                "PUNTAJE TOTAL"
            ]
        )


    col_rango = buscar_columna(
        columnas,
        [
            "RANGO",
            "RANGO_PUNTAJE",
            "RANGO PUNTAJE"
        ]
    )


    # --------------------------------------------------------
    # Seleccionar solo columnas necesarias
    # --------------------------------------------------------

    limpio = df[
        [
            col_codigo,
            col_entidad,
            col_departamento,
            col_grupo,
            col_puntaje,
            col_rango
        ]
    ].copy()


    limpio.columns = [
        "cod_cgr",
        "entidad_inco",
        "departamento_inco",
        "grupo_entidad",
        "puntaje_inco",
        "rango_inco"
    ]


    limpio["anio"] = anio


    # --------------------------------------------------------
    # Normalización textual
    # --------------------------------------------------------

    limpio["grupo_entidad_norm"] = (
        limpio["grupo_entidad"]
        .apply(normalizar_texto)
    )


    limpio["departamento_norm"] = (
        limpio["departamento_inco"]
        .apply(normalizar_texto)
    )


    limpio["entidad_norm"] = (
        limpio["entidad_inco"]
        .apply(normalizar_texto)
    )


    # ========================================================
    # 7. SOLO SEDE CENTRAL
    # ========================================================

    n_antes_sede = len(limpio)


    limpio = limpio[
        limpio["grupo_entidad_norm"]
        == "SEDE CENTRAL"
    ].copy()


    print(
        f"Registros originales: "
        f"{n_antes_sede:,}"
    )

    print(
        f"Registros SEDE CENTRAL: "
        f"{len(limpio):,}"
    )


    # ========================================================
    # 8. EXCLUIR LIMA METROPOLITANA
    # ========================================================

    # No se elimina Lima Provincias.
    # Solo cualquier registro que explícitamente corresponda
    # a Lima Metropolitana.

    es_lima_metropolitana = (
        limpio["departamento_norm"]
        .fillna("")
        .str.contains(
            "LIMA METROPOLITANA",
            regex=False
        )
        |
        limpio["entidad_norm"]
        .fillna("")
        .str.contains(
            "LIMA METROPOLITANA",
            regex=False
        )
        |
        limpio["entidad_norm"]
        .fillna("")
        .str.contains(
            "MUNICIPALIDAD METROPOLITANA DE LIMA",
            regex=False
        )
    )


    n_lima_metropolitana = (
        es_lima_metropolitana.sum()
    )


    limpio = limpio[
        ~es_lima_metropolitana
    ].copy()


    print(
        f"Lima Metropolitana excluida: "
        f"{n_lima_metropolitana:,}"
    )


    # ========================================================
    # 9. CREAR CLAVE GORE
    # ========================================================

    limpio["gore"] = (
        limpio["departamento_norm"]
    )


    # El Gobierno Regional de Lima corresponde a
    # Lima Provincias, pero nuestra base contractual
    # utiliza LIMA como departamento.
    limpio.loc[
        limpio["gore"] == "LIMA PROVINCIAS",
        "gore"
    ] = "LIMA"


    # --------------------------------------------------------
    # Puntaje numérico
    # --------------------------------------------------------

    limpio["puntaje_inco"] = pd.to_numeric(
        limpio["puntaje_inco"],
        errors="coerce"
    )


    # --------------------------------------------------------
    # Limpiar rango
    # --------------------------------------------------------

    limpio["rango_inco"] = (
        limpio["rango_inco"]
        .astype("string")
        .str.strip()
    )


    # --------------------------------------------------------
    # Validar duplicados GORE-año
    # --------------------------------------------------------

    duplicados = (
        limpio
        .duplicated(
            subset=[
                "gore",
                "anio"
            ],
            keep=False
        )
    )


    if duplicados.any():

        print("\nERROR: existen varios registros SEDE CENTRAL")
        print("para un mismo GORE y año:\n")

        print(
            limpio.loc[
                duplicados,
                [
                    "gore",
                    "anio",
                    "cod_cgr",
                    "entidad_inco",
                    "puntaje_inco"
                ]
            ].to_string(
                index=False
            )
        )

        raise ValueError(
            f"INCO {anio} contiene duplicados GORE-año."
        )


    print(
        f"GORE finales para {anio}: "
        f"{limpio['gore'].nunique():,}"
    )


    # --------------------------------------------------------
    # Selección final de esa hoja
    # --------------------------------------------------------

    limpio = limpio[
        [
            "gore",
            "anio",
            "cod_cgr",
            "entidad_inco",
            "puntaje_inco",
            "rango_inco"
        ]
    ].copy()


    bases_inco.append(
        limpio
    )


# ============================================================
# 10. UNIR LOS TRES AÑOS DEL INCO
# ============================================================

inco = pd.concat(
    bases_inco,
    ignore_index=True
)


inco["anio"] = (
    pd.to_numeric(
        inco["anio"],
        errors="coerce"
    )
    .astype("Int64")
)


# Validar nuevamente
duplicados_inco = (
    inco
    .duplicated(
        subset=[
            "gore",
            "anio"
        ]
    )
    .sum()
)


if duplicados_inco > 0:

    raise ValueError(
        "ERROR: la base INCO consolidada contiene "
        "duplicados GORE + año."
    )


# ============================================================
# 11. GUARDAR INCO LIMPIO
# ============================================================

inco = (
    inco
    .sort_values(
        by=[
            "anio",
            "gore"
        ]
    )
    .reset_index(drop=True)
)


inco.to_csv(
    SALIDA_INCO_LIMPIO,
    index=False,
    encoding="utf-8-sig"
)


print("\n" + "=" * 78)
print("BASE INCO LIMPIA")
print("=" * 78)

print(
    f"Filas INCO: "
    f"{len(inco):,}"
)

print(
    f"Duplicados GORE-año: "
    f"{duplicados_inco:,}"
)


print("\nObservaciones por año:")

print(
    inco["anio"]
    .value_counts()
    .sort_index()
    .to_string()
)


# ============================================================
# 12. CREAR CLAVE NORMALIZADA EN BASE MAESTRA
# ============================================================

base["gore_join"] = (
    base["gore"]
    .apply(normalizar_texto)
)


# En caso de que alguna contratación use LIMA PROVINCIAS
base.loc[
    base["gore_join"] == "LIMA PROVINCIAS",
    "gore_join"
] = "LIMA"


inco_merge = inco.rename(
    columns={
        "gore": "gore_join"
    }
)


# ============================================================
# 13. MERGE INCO CON EMPRESA-GORE-AÑO
# ============================================================

base_final = base.merge(
    inco_merge[
        [
            "gore_join",
            "anio",
            "puntaje_inco",
            "rango_inco"
        ]
    ],
    on=[
        "gore_join",
        "anio"
    ],
    how="left",
    validate="many_to_one"
)


# ============================================================
# 14. CONTROL DE OBSERVACIONES SIN INCO
# ============================================================

sin_inco = base_final[
    base_final["puntaje_inco"].isna()
].copy()


print("\n" + "=" * 78)
print("CONTROL DEL MERGE CON INCO")
print("=" * 78)

print(
    f"Filas antes del merge: "
    f"{len(base):,}"
)

print(
    f"Filas después del merge: "
    f"{len(base_final):,}"
)

print(
    f"Con puntaje INCO: "
    f"{base_final['puntaje_inco'].notna().sum():,}"
)

print(
    f"Sin puntaje INCO: "
    f"{base_final['puntaje_inco'].isna().sum():,}"
)


print("\nSin INCO por año:")

print(
    sin_inco["anio"]
    .value_counts()
    .sort_index()
    .to_string()
)


# ============================================================
# 15. MOSTRAR GORE SIN MATCH
# ============================================================

if not sin_inco.empty:

    gores_sin_inco = (
        sin_inco[
            [
                "anio",
                "gore"
            ]
        ]
        .drop_duplicates()
        .sort_values(
            [
                "anio",
                "gore"
            ]
        )
    )

    print("\nGORE-año sin correspondencia INCO:")

    print(
        gores_sin_inco.to_string(
            index=False
        )
    )


    sin_inco.to_csv(
        SALIDA_SIN_INCO,
        index=False,
        encoding="utf-8-sig"
    )


# ============================================================
# 16. ELIMINAR CLAVE AUXILIAR
# ============================================================

base_final = base_final.drop(
    columns=[
        "gore_join"
    ]
)


# ============================================================
# 17. VALIDAR DUPLICADOS FINALES
# ============================================================

duplicados_finales = (
    base_final
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
        "ERROR: aparecieron duplicados RUC + año + GORE "
        "después del merge con INCO."
    )


# ============================================================
# 18. MOVER INCO AL FINAL
# ============================================================

columnas_inco = [
    "puntaje_inco",
    "rango_inco"
]


otras_columnas = [
    columna
    for columna in base_final.columns
    if columna not in columnas_inco
]


base_final = base_final[
    otras_columnas
    + columnas_inco
].copy()


# ============================================================
# 19. TABLA DE NULOS
# ============================================================

nulos = tabla_nulos(
    base_final
)


print("\n" + "=" * 78)
print("VALORES FALTANTES - BASE FINAL")
print("=" * 78)

print(
    nulos.to_string(
        index=False
    )
)


# ============================================================
# 20. RESUMEN DE INCO POR AÑO
# ============================================================

print("\n" + "=" * 78)
print("COBERTURA INCO POR AÑO")
print("=" * 78)


resumen_inco = (
    base_final
    .groupby(
        "anio",
        dropna=False
    )
    .agg(
        observaciones=(
            "ruc",
            "size"
        ),
        con_inco=(
            "puntaje_inco",
            "count"
        )
    )
    .reset_index()
)


resumen_inco["sin_inco"] = (
    resumen_inco["observaciones"]
    -
    resumen_inco["con_inco"]
)


resumen_inco["porcentaje_con_inco"] = (
    resumen_inco["con_inco"]
    /
    resumen_inco["observaciones"]
    * 100
).round(2)


print(
    resumen_inco.to_string(
        index=False
    )
)


# ============================================================
# 21. GUARDAR BASE FINAL
# ============================================================

base_final.to_csv(
    SALIDA_FINAL,
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 22. RESUMEN FINAL
# ============================================================

print("\n" + "=" * 78)
print("BASE MAESTRA GENERADA CORRECTAMENTE")
print("=" * 78)

print(
    f"Filas finales: "
    f"{len(base_final):,}"
)

print(
    f"RUC distintos: "
    f"{base_final['ruc'].nunique():,}"
)

print(
    f"Duplicados RUC-año-GORE: "
    f"{duplicados_finales:,}"
)

print(
    f"Con INCO: "
    f"{base_final['puntaje_inco'].notna().sum():,}"
)

print(
    f"Sin INCO: "
    f"{base_final['puntaje_inco'].isna().sum():,}"
)


print("\nArchivos generados:")

print(
    f"1. INCO limpio:\n"
    f"   {SALIDA_INCO_LIMPIO}"
)

print(
    f"\n2. Base maestra:\n"
    f"   {SALIDA_FINAL}"
)

if not sin_inco.empty:

    print(
        f"\n3. Control de casos sin INCO:\n"
        f"   {SALIDA_SIN_INCO}"
    )


print(
    "\nUnidad de observación final: "
    "RUC × GORE × año."
)