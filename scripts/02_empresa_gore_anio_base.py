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

ARCHIVO_CONTRATACIONES = (
    INSUMOS_DIR / "contrataciones_2004_2024.csv"
)

ARCHIVO_RUCS = (
    INSUMOS_DIR / "rucs_2021_2022_2024.json"
)

SALIDA_LARGO = (
    INTERMEDIATE_DIR / "contrataciones_largo_2021_2022_2024.csv"
)

SALIDA_EMPRESA_GORE = (
    INTERMEDIATE_DIR / "empresa_gore_anio_base.csv"
)


# ============================================================
# 2. CONFIGURACIÓN
# ============================================================

ANIOS_ANALISIS = [2021, 2022, 2024]

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
    Convierte el RUC a texto y elimina espacios y '.0'.
    """
    if pd.isna(valor):
        return pd.NA

    ruc = str(valor).strip()

    if ruc.endswith(".0"):
        ruc = ruc[:-2]

    if ruc == "":
        return pd.NA

    return ruc


def leer_csv_seguro(ruta):
    """
    Intenta leer el archivo con codificaciones comunes.
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
                dtype=str,
                low_memory=False
            )

            print(
                f"CSV leído correctamente con encoding: "
                f"{encoding}"
            )

            return df

        except UnicodeDecodeError as error:
            ultimo_error = error

    raise ultimo_error


def limpiar_monto(valor):
    """
    Convierte montos como '2,600,000.00' a 2600000.00.
    """
    if pd.isna(valor):
        return pd.NA

    texto = str(valor).strip()

    if texto == "":
        return pd.NA

    texto = texto.replace(",", "")
    texto = texto.replace("S/", "")
    texto = texto.replace("S/.", "")
    texto = texto.strip()

    return pd.to_numeric(
        texto,
        errors="coerce"
    )


# ============================================================
# 4. CARGAR LISTA MAESTRA DE RUC
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


rucs_objetivo = set(lista_rucs)


print("\n" + "=" * 75)
print("LISTA DE RUC OBJETIVO")
print("=" * 75)

print(
    f"RUC objetivo únicos: "
    f"{len(rucs_objetivo):,}"
)


# ============================================================
# 5. CARGAR CONTRATACIONES
# ============================================================

contratos = leer_csv_seguro(
    ARCHIVO_CONTRATACIONES
)


print("\n" + "=" * 75)
print("BASE ORIGINAL DE CONTRATACIONES")
print("=" * 75)

print(
    f"Filas originales: "
    f"{len(contratos):,}"
)

print(
    f"Columnas originales: "
    f"{len(contratos.columns):,}"
)


# ============================================================
# 6. VALIDAR COLUMNAS NECESARIAS
# ============================================================

columnas_necesarias = [
    "DEPARTAMENTO",
    "FECHA",
    "MONTO"
] + COLUMNAS_EMPRESA


faltantes = [
    columna
    for columna in columnas_necesarias
    if columna not in contratos.columns
]


if faltantes:

    raise ValueError(
        "Faltan estas columnas en contrataciones_2004_2024.csv:\n"
        + "\n".join(faltantes)
    )


# ============================================================
# 7. CREAR ID DE CONTRATO
# ============================================================

# Cada fila original representa una contratación.
# Creamos el ID antes de expandir EMPRESA_1 ... EMPRESA_9.

contratos = contratos.reset_index(drop=True)

contratos["id_contrato"] = (
    contratos.index + 1
)


# ============================================================
# 8. LIMPIAR FECHA Y CREAR AÑO
# ============================================================

contratos["fecha"] = pd.to_datetime(
    contratos["FECHA"],
    format="%d/%m/%Y",
    errors="coerce"
)


contratos["anio"] = (
    contratos["fecha"]
    .dt.year
    .astype("Int64")
)


fechas_invalidas = (
    contratos["fecha"]
    .isna()
    .sum()
)


print(
    f"Fechas que no pudieron convertirse: "
    f"{fechas_invalidas:,}"
)


# ============================================================
# 9. FILTRAR 2021, 2022 Y 2024
# ============================================================

contratos_periodo = contratos[
    contratos["anio"].isin(
        ANIOS_ANALISIS
    )
].copy()


print("\n" + "=" * 75)
print("FILTRO TEMPORAL")
print("=" * 75)

print(
    f"Contrataciones 2021, 2022 y 2024: "
    f"{len(contratos_periodo):,}"
)


print("\nContrataciones por año:")

print(
    contratos_periodo["anio"]
    .value_counts()
    .sort_index()
    .to_string()
)


# ============================================================
# 10. LIMPIAR DEPARTAMENTO Y MONTO
# ============================================================

contratos_periodo["gore"] = (
    contratos_periodo["DEPARTAMENTO"]
    .astype("string")
    .str.strip()
    .str.upper()
)


contratos_periodo["monto_contrato"] = (
    contratos_periodo["MONTO"]
    .apply(limpiar_monto)
)


montos_na = (
    contratos_periodo["monto_contrato"]
    .isna()
    .sum()
)


print(
    f"\nContrataciones sin monto válido: "
    f"{montos_na:,}"
)


# ============================================================
# 11. PASAR EMPRESA_1 ... EMPRESA_9 A FORMATO LARGO
# ============================================================

contratos_largo = contratos_periodo.melt(
    id_vars=[
        "id_contrato",
        "gore",
        "fecha",
        "anio",
        "monto_contrato"
    ],
    value_vars=COLUMNAS_EMPRESA,
    var_name="posicion_empresa",
    value_name="ruc"
)


contratos_largo["ruc"] = (
    contratos_largo["ruc"]
    .apply(limpiar_ruc)
)


# Eliminar espacios vacíos provenientes de EMPRESA_2...EMPRESA_9
contratos_largo = contratos_largo[
    contratos_largo["ruc"].notna()
].copy()


print("\n" + "=" * 75)
print("EXPANSIÓN A FORMATO LARGO")
print("=" * 75)

print(
    f"Filas empresa-contrato antes de controles: "
    f"{len(contratos_largo):,}"
)


# ============================================================
# 12. VALIDAR FORMATO DE RUC
# ============================================================

contratos_largo["ruc_valido_11_digitos"] = (
    contratos_largo["ruc"]
    .str.fullmatch(r"\d{11}")
)


rucs_formato_invalido = (
    contratos_largo.loc[
        ~contratos_largo["ruc_valido_11_digitos"],
        "ruc"
    ]
    .dropna()
    .unique()
)


print(
    f"RUC con formato distinto a 11 dígitos: "
    f"{len(rucs_formato_invalido):,}"
)


if len(rucs_formato_invalido) > 0:

    print("\nEjemplos de RUC con formato inválido:")

    for ruc in rucs_formato_invalido[:20]:
        print(f"  {ruc}")


# ============================================================
# 13. CONTROLAR RUC REPETIDO DENTRO DEL MISMO CONTRATO
# ============================================================

duplicados_empresa_contrato = (
    contratos_largo
    .duplicated(
        subset=[
            "id_contrato",
            "ruc"
        ],
        keep=False
    )
)


n_duplicados_empresa_contrato = (
    duplicados_empresa_contrato.sum()
)


print(
    f"\nFilas con mismo RUC repetido dentro del contrato: "
    f"{n_duplicados_empresa_contrato:,}"
)


# Una empresa debe contar solo una vez dentro del mismo contrato.
contratos_largo = (
    contratos_largo
    .drop_duplicates(
        subset=[
            "id_contrato",
            "ruc"
        ],
        keep="first"
    )
    .copy()
)


# ============================================================
# 14. COMPARAR CON LOS 1,273 RUC OBJETIVO
# ============================================================

contratos_largo["ruc_en_lista_objetivo"] = (
    contratos_largo["ruc"]
    .isin(rucs_objetivo)
)


rucs_fuera_lista = set(
    contratos_largo.loc[
        ~contratos_largo["ruc_en_lista_objetivo"],
        "ruc"
    ]
)


print("\n" + "=" * 75)
print("COBERTURA RESPECTO A LISTA DE 1,273 RUC")
print("=" * 75)


print(
    f"RUC distintos encontrados en contratos: "
    f"{contratos_largo['ruc'].nunique():,}"
)


print(
    f"RUC encontrados que están en lista objetivo: "
    f"{contratos_largo.loc[contratos_largo['ruc_en_lista_objetivo'], 'ruc'].nunique():,}"
)


print(
    f"RUC encontrados fuera de lista objetivo: "
    f"{len(rucs_fuera_lista):,}"
)


rucs_en_contratos = set(
    contratos_largo["ruc"]
)


rucs_objetivo_no_encontrados = (
    rucs_objetivo
    - rucs_en_contratos
)


print(
    f"RUC objetivo que no aparecen en contratos filtrados: "
    f"{len(rucs_objetivo_no_encontrados):,}"
)


# ============================================================
# 15. QUEDARNOS CON EL UNIVERSO OBJETIVO
# ============================================================

contratos_largo = contratos_largo[
    contratos_largo["ruc_en_lista_objetivo"]
].copy()


# Ya no necesitamos las variables de control en la salida.
contratos_largo = contratos_largo[
    [
        "id_contrato",
        "ruc",
        "gore",
        "fecha",
        "anio",
        "monto_contrato"
    ]
].copy()


# ============================================================
# 16. VALIDACIÓN FINAL DE CONTRATACIONES LARGAS
# ============================================================

duplicados_finales = (
    contratos_largo
    .duplicated(
        subset=[
            "id_contrato",
            "ruc"
        ]
    )
    .sum()
)


if duplicados_finales > 0:

    raise ValueError(
        "ERROR: todavía existen duplicados "
        "id_contrato + ruc."
    )


# ============================================================
# 17. CREAR NÚMERO DE CONTRATOS POR EMPRESA-GORE-AÑO
# ============================================================

empresa_gore_anio = (
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
        n_contratos=(
            "id_contrato",
            "nunique"
        )
    )
)


# ============================================================
# 18. CALCULAR NÚMERO DE GORES POR EMPRESA-AÑO
# ============================================================

gores_por_anio = (
    empresa_gore_anio
    .groupby(
        [
            "ruc",
            "anio"
        ],
        as_index=False
    )
    .agg(
        n_gores_anio=(
            "gore",
            "nunique"
        )
    )
)


empresa_gore_anio = (
    empresa_gore_anio
    .merge(
        gores_por_anio,
        on=[
            "ruc",
            "anio"
        ],
        how="left",
        validate="many_to_one"
    )
)


# ============================================================
# 19. TIPOS DE DATOS
# ============================================================

contratos_largo["anio"] = (
    contratos_largo["anio"]
    .astype("Int64")
)


empresa_gore_anio["anio"] = (
    empresa_gore_anio["anio"]
    .astype("Int64")
)


empresa_gore_anio["n_contratos"] = (
    empresa_gore_anio["n_contratos"]
    .astype("Int64")
)


empresa_gore_anio["n_gores_anio"] = (
    empresa_gore_anio["n_gores_anio"]
    .astype("Int64")
)


# ============================================================
# 20. ORDENAR
# ============================================================

contratos_largo = (
    contratos_largo
    .sort_values(
        by=[
            "anio",
            "gore",
            "ruc",
            "fecha",
            "id_contrato"
        ]
    )
    .reset_index(drop=True)
)


empresa_gore_anio = (
    empresa_gore_anio
    .sort_values(
        by=[
            "anio",
            "gore",
            "ruc"
        ]
    )
    .reset_index(drop=True)
)


# ============================================================
# 21. VALIDAR BASE EMPRESA-GORE-AÑO
# ============================================================

duplicados_empresa_gore = (
    empresa_gore_anio
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
        "ERROR: existen duplicados ruc + anio + gore "
        "en empresa_gore_anio."
    )


# ============================================================
# 22. NULOS
# ============================================================

print("\n" + "=" * 75)
print("VALORES FALTANTES - CONTRATACIONES LARGO")
print("=" * 75)


tabla_nulos_largo = pd.DataFrame({
    "variable": contratos_largo.columns,
    "n_na": [
        contratos_largo[col].isna().sum()
        for col in contratos_largo.columns
    ],
    "porcentaje_na": [
        round(
            contratos_largo[col].isna().mean() * 100,
            2
        )
        for col in contratos_largo.columns
    ]
})


print(
    tabla_nulos_largo.to_string(
        index=False
    )
)


print("\n" + "=" * 75)
print("VALORES FALTANTES - EMPRESA GORE AÑO")
print("=" * 75)


tabla_nulos_empresa_gore = pd.DataFrame({
    "variable": empresa_gore_anio.columns,
    "n_na": [
        empresa_gore_anio[col].isna().sum()
        for col in empresa_gore_anio.columns
    ],
    "porcentaje_na": [
        round(
            empresa_gore_anio[col].isna().mean() * 100,
            2
        )
        for col in empresa_gore_anio.columns
    ]
})


print(
    tabla_nulos_empresa_gore.to_string(
        index=False
    )
)


# ============================================================
# 23. GUARDAR
# ============================================================

contratos_largo.to_csv(
    SALIDA_LARGO,
    index=False,
    encoding="utf-8-sig",
    date_format="%d/%m/%Y"
)


empresa_gore_anio.to_csv(
    SALIDA_EMPRESA_GORE,
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 24. RESUMEN FINAL
# ============================================================

print("\n" + "=" * 75)
print("RESUMEN FINAL")
print("=" * 75)


print(
    f"Contratos originales 2021/2022/2024 : "
    f"{len(contratos_periodo):,}"
)


print(
    f"Filas empresa-contrato finales       : "
    f"{len(contratos_largo):,}"
)


print(
    f"RUC distintos finales                : "
    f"{contratos_largo['ruc'].nunique():,}"
)


print(
    f"Empresa-GORE-año                     : "
    f"{len(empresa_gore_anio):,}"
)


print(
    f"Duplicados contrato-RUC              : "
    f"{duplicados_finales:,}"
)


print(
    f"Duplicados RUC-año-GORE              : "
    f"{duplicados_empresa_gore:,}"
)


print("\nArchivos generados:")

print(
    f"1. {SALIDA_LARGO}"
)

print(
    f"2. {SALIDA_EMPRESA_GORE}"
)

print("\nProceso terminado correctamente.")