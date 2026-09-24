from pathlib import Path
import pandas as pd
import numpy as np


# ============================================================
# 1. RUTAS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"

ARCHIVO_BASE = (
    DATA_DIR / "data_final_consolidada.csv"
)


# ============================================================
# 2. CONFIGURACIÓN
# ============================================================

ANIOS_ESPERADOS = {
    2021,
    2022,
    2024
}


# ============================================================
# 3. FUNCIONES AUXILIARES
# ============================================================

def leer_csv_seguro(ruta, dtype=None):

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


def guardar_csv(df, ruta):

    df.to_csv(
        ruta,
        index=False,
        encoding="utf-8-sig"
    )


def agregar_control(
    lista,
    control,
    resultado,
    valor_observado=None,
    detalle=None
):

    lista.append({
        "control": control,
        "resultado": resultado,
        "valor_observado": valor_observado,
        "detalle": detalle
    })


def imprimir_seccion(titulo):

    print("\n" + "=" * 80)
    print(titulo)
    print("=" * 80)


# ============================================================
# 4. CARGAR BASE
# ============================================================

base = leer_csv_seguro(
    ARCHIVO_BASE,
    dtype={
        "ruc": str,
        "gore": str
    }
)


# ============================================================
# 5. TIPOS DE DATOS
# ============================================================

columnas_numericas = [
    "anio",
    "anio_inicio_actividades",
    "antiguedad_empresa",
    "inicio_posterior_contratacion",
    "primer_anio_contratacion",
    "experiencia_contratacion",
    "n_contratos",
    "n_gores_anio",
    "cmc",
    "n_contratos_cmc_evaluables",
    "n_supera_cmc",
    "prop_supera_cmc",
    "cantidad_rubros",
    "sanciones_tcp_acum",
    "penalidades_acum",
    "inhabilitacion_judicial",
    "inhabilitacion_administrativa",
    "sunat_ok",
    "tiene_info_sunat",
    "tiene_info_proveedores_estado",
    "puntaje_inco"
]


for columna in columnas_numericas:

    if columna in base.columns:

        base[columna] = pd.to_numeric(
            base[columna],
            errors="coerce"
        )


# ============================================================
# 6. RESUMEN GENERAL
# ============================================================

imprimir_seccion(
    "RESUMEN GENERAL DE LA BASE"
)

print(
    f"Filas: "
    f"{len(base):,}"
)

print(
    f"Columnas: "
    f"{len(base.columns):,}"
)

print(
    f"RUC distintos: "
    f"{base['ruc'].nunique():,}"
)

print(
    f"GORE distintos: "
    f"{base['gore'].nunique():,}"
)

print(
    f"Años: "
    f"{sorted(base['anio'].dropna().unique().astype(int))}"
)


controles = []
errores = []


# ============================================================
# 7. CONTROL DE DUPLICADOS
# ============================================================

imprimir_seccion(
    "1. CONTROL DE UNIDAD DE OBSERVACIÓN"
)


duplicados = (
    base
    .duplicated(
        subset=[
            "ruc",
            "anio",
            "gore"
        ],
        keep=False
    )
)


n_duplicados = (
    duplicados.sum()
)


print(
    f"Filas duplicadas RUC-año-GORE: "
    f"{n_duplicados:,}"
)


agregar_control(
    controles,
    "Duplicados RUC-año-GORE",
    "OK" if n_duplicados == 0 else "ERROR",
    n_duplicados,
    "La unidad de observación debe ser única."
)


if n_duplicados > 0:

    error = base.loc[
        duplicados
    ].copy()

    error["tipo_error"] = (
        "Duplicado RUC-año-GORE"
    )

    errores.append(
        error
    )


# ============================================================
# 8. CONTROL DE AÑOS
# ============================================================

anios_observados = set(
    base["anio"]
    .dropna()
    .astype(int)
    .unique()
)


anios_inesperados = (
    anios_observados
    - ANIOS_ESPERADOS
)


print(
    f"Años inesperados: "
    f"{sorted(anios_inesperados)}"
)


agregar_control(
    controles,
    "Años válidos",
    "OK" if len(anios_inesperados) == 0 else "ERROR",
    str(sorted(anios_observados)),
    "Se esperan únicamente 2021, 2022 y 2024."
)


# ============================================================
# 9. CONTROL n_gores_anio
# ============================================================

imprimir_seccion(
    "2. CONTROL DE NÚMERO DE GORES POR EMPRESA-AÑO"
)


control_gores = (
    base
    .groupby(
        [
            "ruc",
            "anio"
        ],
        as_index=False
    )
    .agg(
        n_gores_calculado=(
            "gore",
            "nunique"
        )
    )
)


control_gores_base = base.merge(
    control_gores,
    on=[
        "ruc",
        "anio"
    ],
    how="left",
    validate="many_to_one"
)


error_gores = control_gores_base[
    control_gores_base["n_gores_anio"]
    !=
    control_gores_base["n_gores_calculado"]
].copy()


print(
    f"Filas con n_gores_anio incorrecto: "
    f"{len(error_gores):,}"
)


agregar_control(
    controles,
    "n_gores_anio coincide con número real de GORE",
    "OK" if len(error_gores) == 0 else "ERROR",
    len(error_gores)
)


if not error_gores.empty:

    error_gores["tipo_error"] = (
        "n_gores_anio incorrecto"
    )

    errores.append(
        error_gores
    )


# ============================================================
# 10. CONTROL CMC
# ============================================================

imprimir_seccion(
    "3. CONTROL DE VARIABLES CMC"
)


# ------------------------------------------------------------
# 10.1 n_supera_cmc <= contratos evaluables
# ------------------------------------------------------------

error_supera_evaluables = base[
    base["n_supera_cmc"].notna()
    &
    (
        base["n_supera_cmc"]
        >
        base["n_contratos_cmc_evaluables"]
    )
].copy()


print(
    "Casos donde n_supera_cmc > "
    f"n_contratos_cmc_evaluables: "
    f"{len(error_supera_evaluables):,}"
)


agregar_control(
    controles,
    "n_supera_cmc <= n_contratos_cmc_evaluables",
    "OK" if error_supera_evaluables.empty else "ERROR",
    len(error_supera_evaluables)
)


if not error_supera_evaluables.empty:

    error_supera_evaluables["tipo_error"] = (
        "n_supera_cmc mayor que evaluables"
    )

    errores.append(
        error_supera_evaluables
    )


# ------------------------------------------------------------
# 10.2 evaluables <= n_contratos
# ------------------------------------------------------------

error_evaluables_contratos = base[
    base["n_contratos_cmc_evaluables"]
    >
    base["n_contratos"]
].copy()


print(
    "Casos donde evaluables > n_contratos: "
    f"{len(error_evaluables_contratos):,}"
)


agregar_control(
    controles,
    "n_contratos_cmc_evaluables <= n_contratos",
    "OK" if error_evaluables_contratos.empty else "ERROR",
    len(error_evaluables_contratos)
)


if not error_evaluables_contratos.empty:

    error_evaluables_contratos["tipo_error"] = (
        "CMC evaluables mayor que n_contratos"
    )

    errores.append(
        error_evaluables_contratos
    )


# ------------------------------------------------------------
# 10.3 proporción entre 0 y 1
# ------------------------------------------------------------

error_prop_rango = base[
    base["prop_supera_cmc"].notna()
    &
    (
        (base["prop_supera_cmc"] < 0)
        |
        (base["prop_supera_cmc"] > 1)
    )
].copy()


print(
    f"Proporciones fuera de [0,1]: "
    f"{len(error_prop_rango):,}"
)


agregar_control(
    controles,
    "prop_supera_cmc entre 0 y 1",
    "OK" if error_prop_rango.empty else "ERROR",
    len(error_prop_rango)
)


if not error_prop_rango.empty:

    error_prop_rango["tipo_error"] = (
        "prop_supera_cmc fuera de rango"
    )

    errores.append(
        error_prop_rango
    )


# ------------------------------------------------------------
# 10.4 comprobar fórmula
# ------------------------------------------------------------

mask_prop = (
    base["n_contratos_cmc_evaluables"] > 0
    &
    base["n_supera_cmc"].notna()
)


prop_calculada = (
    base.loc[
        mask_prop,
        "n_supera_cmc"
    ]
    /
    base.loc[
        mask_prop,
        "n_contratos_cmc_evaluables"
    ]
)


diferencia_prop = (
    base.loc[
        mask_prop,
        "prop_supera_cmc"
    ]
    -
    prop_calculada
).abs()


indices_error_prop = (
    diferencia_prop[
        diferencia_prop > 1e-10
    ]
    .index
)


error_formula_prop = base.loc[
    indices_error_prop
].copy()


print(
    f"Casos con fórmula de proporción incorrecta: "
    f"{len(error_formula_prop):,}"
)


agregar_control(
    controles,
    "prop_supera_cmc coincide con fórmula",
    "OK" if error_formula_prop.empty else "ERROR",
    len(error_formula_prop)
)


if not error_formula_prop.empty:

    error_formula_prop["tipo_error"] = (
        "Fórmula prop_supera_cmc incorrecta"
    )

    errores.append(
        error_formula_prop
    )


# ------------------------------------------------------------
# 10.5 CMC faltante
# ------------------------------------------------------------

sin_cmc = base[
    base["cmc"].isna()
].copy()


print(
    f"Filas sin CMC: "
    f"{len(sin_cmc):,}"
)


# ------------------------------------------------------------
# 10.6 CMC = 0
# ------------------------------------------------------------

cmc_cero = base[
    base["cmc"] == 0
].copy()


print(
    f"Filas con CMC = 0: "
    f"{len(cmc_cero):,}"
)


agregar_control(
    controles,
    "Filas sin CMC",
    "REVISAR" if len(sin_cmc) > 0 else "OK",
    len(sin_cmc),
    "Un CMC faltante no debe interpretarse como cero."
)


agregar_control(
    controles,
    "Filas con CMC = 0",
    "REVISAR" if len(cmc_cero) > 0 else "OK",
    len(cmc_cero)
)


# ============================================================
# 11. CONTROL TRAYECTORIA TEMPORAL
# ============================================================

imprimir_seccion(
    "4. CONTROL DE TRAYECTORIA TEMPORAL"
)


# ------------------------------------------------------------
# 11.1 experiencia negativa
# ------------------------------------------------------------

experiencia_negativa = base[
    base["experiencia_contratacion"] < 0
].copy()


print(
    f"Experiencia contractual negativa: "
    f"{len(experiencia_negativa):,}"
)


agregar_control(
    controles,
    "experiencia_contratacion >= 0",
    "OK" if experiencia_negativa.empty else "ERROR",
    len(experiencia_negativa)
)


if not experiencia_negativa.empty:

    experiencia_negativa["tipo_error"] = (
        "Experiencia contractual negativa"
    )

    errores.append(
        experiencia_negativa
    )


# ------------------------------------------------------------
# 11.2 fórmula experiencia
# ------------------------------------------------------------

mask_exp = (
    base["primer_anio_contratacion"].notna()
    &
    base["anio"].notna()
    &
    base["experiencia_contratacion"].notna()
)


exp_calculada = (
    base.loc[
        mask_exp,
        "anio"
    ]
    -
    base.loc[
        mask_exp,
        "primer_anio_contratacion"
    ]
)


error_exp_formula = base.loc[
    mask_exp
].copy()


error_exp_formula = error_exp_formula[
    error_exp_formula["experiencia_contratacion"]
    !=
    exp_calculada
]


print(
    f"Experiencia con fórmula incorrecta: "
    f"{len(error_exp_formula):,}"
)


agregar_control(
    controles,
    "experiencia = año - primer año",
    "OK" if error_exp_formula.empty else "ERROR",
    len(error_exp_formula)
)


# ------------------------------------------------------------
# 11.3 antigüedad negativa
# ------------------------------------------------------------

antiguedad_negativa = base[
    base["antiguedad_empresa"] < 0
].copy()


print(
    f"Antigüedad negativa almacenada: "
    f"{len(antiguedad_negativa):,}"
)


agregar_control(
    controles,
    "antiguedad_empresa no negativa",
    "OK" if antiguedad_negativa.empty else "ERROR",
    len(antiguedad_negativa)
)


if not antiguedad_negativa.empty:

    antiguedad_negativa["tipo_error"] = (
        "Antigüedad negativa"
    )

    errores.append(
        antiguedad_negativa
    )


# ------------------------------------------------------------
# 11.4 inicio posterior
# ------------------------------------------------------------

inicio_posterior = base[
    base["inicio_posterior_contratacion"] == 1
].copy()


print(
    f"Filas con inicio posterior a contratación: "
    f"{len(inicio_posterior):,}"
)


agregar_control(
    controles,
    "Inicio posterior al año de contratación",
    "REVISAR" if len(inicio_posterior) > 0 else "OK",
    len(inicio_posterior),
    "Se conserva como inconsistencia de fuente; antigüedad debe ser NA."
)


# comprobar que en esos casos antigüedad sea NA

error_inicio_antiguedad = base[
    (base["inicio_posterior_contratacion"] == 1)
    &
    base["antiguedad_empresa"].notna()
].copy()


print(
    "Inicio posterior pero antigüedad no es NA: "
    f"{len(error_inicio_antiguedad):,}"
)


agregar_control(
    controles,
    "Inicio posterior implica antigüedad NA",
    "OK" if error_inicio_antiguedad.empty else "ERROR",
    len(error_inicio_antiguedad)
)


if not error_inicio_antiguedad.empty:

    error_inicio_antiguedad["tipo_error"] = (
        "Inicio posterior con antigüedad no NA"
    )

    errores.append(
        error_inicio_antiguedad
    )


# ============================================================
# 12. CONTROL SUNAT
# ============================================================

imprimir_seccion(
    "5. COBERTURA SUNAT"
)


sin_sunat = base[
    base["tiene_info_sunat"] == 0
].copy()


rucs_sin_sunat = (
    sin_sunat[
        [
            "ruc",
            "razon_social",
            "anio",
            "gore",
            "sunat_ok",
            "tiene_info_sunat"
        ]
    ]
    .drop_duplicates()
)


print(
    f"Filas sin información SUNAT: "
    f"{len(sin_sunat):,}"
)

print(
    f"RUC distintos sin SUNAT: "
    f"{sin_sunat['ruc'].nunique():,}"
)


agregar_control(
    controles,
    "RUC distintos sin información SUNAT",
    "REVISAR" if sin_sunat["ruc"].nunique() > 0 else "OK",
    sin_sunat["ruc"].nunique()
)


# ============================================================
# 13. CONTROL INCO
# ============================================================

imprimir_seccion(
    "6. CONTROL INCO"
)


sin_inco = base[
    base["puntaje_inco"].isna()
].copy()


print(
    f"Filas sin puntaje INCO: "
    f"{len(sin_inco):,}"
)


agregar_control(
    controles,
    "Cobertura INCO",
    "OK" if sin_inco.empty else "ERROR",
    len(sin_inco)
)


# Cada GORE-año debe tener un único puntaje y rango INCO.

control_inco = (
    base
    .groupby(
        [
            "anio",
            "gore"
        ],
        as_index=False
    )
    .agg(
        n_puntajes_inco=(
            "puntaje_inco",
            "nunique"
        ),
        n_rangos_inco=(
            "rango_inco",
            "nunique"
        ),
        puntaje_inco=(
            "puntaje_inco",
            "first"
        ),
        rango_inco=(
            "rango_inco",
            "first"
        ),
        n_empresas=(
            "ruc",
            "nunique"
        ),
        n_observaciones=(
            "ruc",
            "size"
        )
    )
)


error_inco = control_inco[
    (control_inco["n_puntajes_inco"] != 1)
    |
    (control_inco["n_rangos_inco"] != 1)
].copy()


print(
    "GORE-año con más de un valor INCO: "
    f"{len(error_inco):,}"
)


agregar_control(
    controles,
    "Un único INCO por GORE-año",
    "OK" if error_inco.empty else "ERROR",
    len(error_inco)
)


# ============================================================
# 14. CASOS QUE SUPERAN CMC
# ============================================================

imprimir_seccion(
    "7. DISTRIBUCIÓN DE SUPERACIÓN DE CMC"
)


casos_supera_cmc = base[
    base["n_supera_cmc"] > 0
].copy()


print(
    f"Empresa-GORE-año con >=1 contrato que supera CMC: "
    f"{len(casos_supera_cmc):,}"
)


print(
    f"RUC distintos con >=1 superación: "
    f"{casos_supera_cmc['ruc'].nunique():,}"
)


print("\nDistribución de prop_supera_cmc:")

print(
    base["prop_supera_cmc"]
    .describe(
        percentiles=[
            0.25,
            0.50,
            0.75,
            0.90,
            0.95,
            0.99
        ]
    )
    .to_string()
)


# ============================================================
# 15. DISTRIBUCIÓN DE CMC
# ============================================================

imprimir_seccion(
    "8. DISTRIBUCIÓN DEL CMC"
)


print(
    base["cmc"]
    .describe(
        percentiles=[
            0.01,
            0.05,
            0.25,
            0.50,
            0.75,
            0.90,
            0.95,
            0.99
        ]
    )
    .to_string()
)


# Para revisión, guardaremos los valores en el 1% superior
# y el 1% inferior, excluyendo NA.

cmc_validos = base[
    base["cmc"].notna()
].copy()


if not cmc_validos.empty:

    p01_cmc = (
        cmc_validos["cmc"]
        .quantile(0.01)
    )

    p99_cmc = (
        cmc_validos["cmc"]
        .quantile(0.99)
    )

    cmc_extremos = cmc_validos[
        (cmc_validos["cmc"] <= p01_cmc)
        |
        (cmc_validos["cmc"] >= p99_cmc)
    ].copy()

    cmc_extremos["tipo_extremo_cmc"] = np.where(
        cmc_extremos["cmc"] <= p01_cmc,
        "1% inferior",
        "1% superior"
    )

else:

    cmc_extremos = pd.DataFrame()


# ============================================================
# 16. SANCIONES Y PENALIDADES
# ============================================================

imprimir_seccion(
    "9. SANCIONES Y PENALIDADES"
)


empresas_unicas = (
    base
    .sort_values(
        [
            "ruc",
            "anio"
        ]
    )
    .drop_duplicates(
        subset=[
            "ruc"
        ]
    )
    .copy()
)


empresas_con_sanciones = empresas_unicas[
    empresas_unicas["sanciones_tcp_acum"] > 0
].copy()


empresas_con_penalidades = empresas_unicas[
    empresas_unicas["penalidades_acum"] > 0
].copy()


print(
    f"Empresas con sanciones TCP acumuladas > 0: "
    f"{len(empresas_con_sanciones):,}"
)


print(
    f"Empresas con penalidades acumuladas > 0: "
    f"{len(empresas_con_penalidades):,}"
)


print(
    "Empresas con inhabilitación judicial > 0: "
    f"{(empresas_unicas['inhabilitacion_judicial'] > 0).sum():,}"
)


print(
    "Empresas con inhabilitación administrativa > 0: "
    f"{(empresas_unicas['inhabilitacion_administrativa'] > 0).sum():,}"
)


# ============================================================
# 17. EMPRESAS CON MÁS GORES
# ============================================================

imprimir_seccion(
    "10. EMPRESAS CON MAYOR COBERTURA TERRITORIAL"
)


empresas_mas_gores = (
    base[
        [
            "ruc",
            "razon_social",
            "anio",
            "n_gores_anio"
        ]
    ]
    .drop_duplicates()
    .sort_values(
        by=[
            "n_gores_anio",
            "anio"
        ],
        ascending=[
            False,
            True
        ]
    )
)


print(
    empresas_mas_gores
    .head(20)
    .to_string(
        index=False
    )
)


# ============================================================
# 18. EMPRESAS CON MÁS CONTRATOS
# ============================================================

contratos_empresa_anio = (
    base
    .groupby(
        [
            "ruc",
            "razon_social",
            "anio"
        ],
        as_index=False,
        dropna=False
    )
    .agg(
        n_contratos_total_anio=(
            "n_contratos",
            "sum"
        ),
        n_gores=(
            "gore",
            "nunique"
        )
    )
    .sort_values(
        "n_contratos_total_anio",
        ascending=False
    )
)


print("\nEmpresas con más contratos por año:")

print(
    contratos_empresa_anio
    .head(20)
    .to_string(
        index=False
    )
)


# ============================================================
# 19. RESUMEN POR AÑO
# ============================================================

imprimir_seccion(
    "11. RESUMEN POR AÑO"
)


resumen_anio = (
    base
    .groupby(
        "anio",
        as_index=False
    )
    .agg(
        observaciones=(
            "ruc",
            "size"
        ),
        empresas=(
            "ruc",
            "nunique"
        ),
        gores=(
            "gore",
            "nunique"
        ),
        contratos=(
            "n_contratos",
            "sum"
        ),
        media_n_contratos=(
            "n_contratos",
            "mean"
        ),
        media_n_gores=(
            "n_gores_anio",
            "mean"
        ),
        media_cmc=(
            "cmc",
            "mean"
        ),
        mediana_cmc=(
            "cmc",
            "median"
        ),
        media_inco=(
            "puntaje_inco",
            "mean"
        )
    )
)


print(
    resumen_anio.to_string(
        index=False
    )
)


# ============================================================
# 20. RESUMEN GORE-AÑO
# ============================================================

resumen_gore_anio = (
    base
    .groupby(
        [
            "anio",
            "gore"
        ],
        as_index=False
    )
    .agg(
        observaciones=(
            "ruc",
            "size"
        ),
        empresas=(
            "ruc",
            "nunique"
        ),
        contratos=(
            "n_contratos",
            "sum"
        ),
        empresas_superan_cmc=(
            "n_supera_cmc",
            lambda x: (x > 0).sum()
        ),
        media_prop_supera_cmc=(
            "prop_supera_cmc",
            "mean"
        ),
        puntaje_inco=(
            "puntaje_inco",
            "first"
        ),
        rango_inco=(
            "rango_inco",
            "first"
        )
    )
    .sort_values(
        [
            "anio",
            "gore"
        ]
    )
)



# ============================================================
# 23. RESUMEN FINAL
# ============================================================

imprimir_seccion(
    "RESULTADO FINAL DE VALIDACIÓN"
)


resumen_controles = pd.DataFrame(
    controles
)


print(
    resumen_controles[
        [
            "control",
            "resultado",
            "valor_observado"
        ]
    ]
    .to_string(
        index=False
    )
)


n_errores = (
    resumen_controles["resultado"]
    .eq("ERROR")
    .sum()
)


n_revisar = (
    resumen_controles["resultado"]
    .eq("REVISAR")
    .sum()
)


n_ok = (
    resumen_controles["resultado"]
    .eq("OK")
    .sum()
)


print("\n" + "-" * 80)

print(
    f"Controles OK      : "
    f"{n_ok:,}"
)

print(
    f"Controles REVISAR : "
    f"{n_revisar:,}"
)

print(
    f"Controles ERROR   : "
    f"{n_errores:,}"
)


if n_errores == 0:

    print(
        "\nRESULTADO: no se detectaron errores "
        "estructurales en la base."
    )

else:

    print(
        "\nATENCIÓN: se detectaron errores estructurales. "
        "Revisar 99_errores_validacion.csv."
    )


print(
    "\nLos controles marcados como REVISAR no implican "
    "necesariamente un error; identifican casos que deben "
    "documentarse o inspeccionarse."
)

