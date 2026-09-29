from pathlib import Path
import json

import pandas as pd
import networkx as nx
from networkx.algorithms import bipartite


# ============================================================
# 1. RUTAS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
INSUMOS_DIR = DATA_DIR / "insumos_originales"
INTERMEDIATE_DIR = DATA_DIR / "bases_intermedias"

ARCHIVO_CONTRATOS = (
    INSUMOS_DIR
    / "contrataciones_2021_2022_2024.csv"
)

ARCHIVO_ENRIQUECIDO = (
    INTERMEDIATE_DIR
    / "contrataciones_2021_2022_2024_enriquecida.csv"
)

SALIDA_METRICAS = (
    INTERMEDIATE_DIR
    / "metricas_red_ruc_gore_anio.csv"
)

SALIDA_ENRIQUECIDA_RED = (
    INTERMEDIATE_DIR
    / "data_final.csv"
)


# ============================================================
# 2. CONFIGURACIÓN
# ============================================================

ANIOS_ANALISIS = [
    2021,
    2022,
    2024
]

COLUMNAS_RUC = [
    "ruc1",
    "ruc2",
    "ruc3",
    "ruc4",
    "ruc5",
    "ruc6",
    "ruc7",
    "ruc8",
    "ruc9"
]

METRICAS_RED = [
    "degree_centrality",
    "weighted_degree",
    "closeness_centrality",
    "hhi_gore",
    "supplier_share_gore",
    "dependencia_empresa_gore",
    "dependencia_gore_empresa",
    "duracion_vinculo",
    "n_gores_atendidos"
]


# ============================================================
# 3. FUNCIONES AUXILIARES
# ============================================================

def limpiar_ruc(valor):
    """
    Limpia valores de RUC y convierte vacíos en None.
    """

    if pd.isna(valor):
        return None

    ruc = str(valor).strip()

    if ruc.endswith(".0"):
        ruc = ruc[:-2]

    if ruc.lower() in {
        "",
        "nan",
        "none",
        "<na>"
    }:
        return None

    return ruc


def normalizar_gore(valor):
    """
    Normaliza el nombre del GORE.
    """

    if pd.isna(valor):
        return None

    gore = str(valor).strip().upper()

    if gore == "":
        return None

    return gore


def valor_json(valor):
    """
    Convierte valores pandas/numpy a tipos compatibles con JSON.
    """

    if pd.isna(valor):
        return None

    if hasattr(valor, "item"):

        try:
            return valor.item()

        except Exception:
            pass

    return valor


def enriquecer_objeto_ruc(
    celda,
    anio,
    gore,
    lookup_metricas
):
    """
    Añade las métricas de red al objeto JSON ya almacenado
    dentro de cada ruc1...ruc9.
    """

    if pd.isna(celda):
        return None

    texto = str(celda).strip()

    if texto == "":
        return None

    try:

        objeto = json.loads(
            texto
        )

    except json.JSONDecodeError:

        raise ValueError(
            f"No se pudo leer como JSON la celda:\n{texto}"
        )


    ruc = limpiar_ruc(
        objeto.get("ruc")
    )

    if ruc is None:
        return None


    clave = (
        ruc,
        int(anio),
        normalizar_gore(gore)
    )


    metricas = lookup_metricas.get(
        clave
    )


    if metricas is None:

        for metrica in METRICAS_RED:
            objeto[metrica] = None

    else:

        for metrica in METRICAS_RED:

            objeto[metrica] = valor_json(
                metricas.get(metrica)
            )


    return json.dumps(
        objeto,
        ensure_ascii=False,
        separators=(",", ":")
    )


# ============================================================
# 4. LEER CONTRATACIONES
# ============================================================

contratos = pd.read_csv(
    ARCHIVO_CONTRATOS,
    dtype=str,
    encoding="utf-8-sig",
    low_memory=False
)


print("\n" + "=" * 78)
print("CONTRATACIONES")
print("=" * 78)

print(
    f"Proyectos: "
    f"{len(contratos):,}"
)

print(
    f"IDs únicos: "
    f"{contratos['id'].nunique():,}"
)


# ============================================================
# 5. PREPARAR FECHA, AÑO Y GORE
# ============================================================

contratos["fecha_dt"] = pd.to_datetime(
    contratos["fecha"],
    format="%d/%m/%Y",
    errors="coerce"
)


contratos["anio"] = (
    contratos["fecha_dt"]
    .dt.year
    .astype("Int64")
)


if contratos["anio"].isna().any():

    raise ValueError(
        "ERROR: existen fechas que no pudieron convertirse."
    )


anios_encontrados = set(
    contratos["anio"]
    .dropna()
    .astype(int)
    .unique()
)


if anios_encontrados != set(ANIOS_ANALISIS):

    raise ValueError(
        f"Años encontrados: {sorted(anios_encontrados)}. "
        f"Se esperaban {ANIOS_ANALISIS}."
    )


contratos["gore"] = (
    contratos["gore"]
    .apply(normalizar_gore)
)


# ============================================================
# 6. LIMPIAR COLUMNAS RUC
# ============================================================

for columna in COLUMNAS_RUC:

    contratos[columna] = (
        contratos[columna]
        .apply(limpiar_ruc)
    )


# ============================================================
# 7. PASAR CONTRATACIONES A FORMATO LARGO
# ============================================================

contratos_largo = contratos.melt(
    id_vars=[
        "id",
        "gore",
        "fecha",
        "anio"
    ],
    value_vars=COLUMNAS_RUC,
    var_name="posicion_ruc",
    value_name="ruc"
)


contratos_largo = contratos_largo[
    contratos_largo["ruc"].notna()
].copy()


# Un mismo RUC no debe contarse dos veces
# dentro del mismo proyecto.
contratos_largo = (
    contratos_largo
    .drop_duplicates(
        subset=[
            "id",
            "ruc"
        ]
    )
    .copy()
)


print("\n" + "=" * 78)
print("FORMATO LARGO")
print("=" * 78)

print(
    f"Participaciones RUC-proyecto: "
    f"{len(contratos_largo):,}"
)

print(
    f"RUC distintos: "
    f"{contratos_largo['ruc'].nunique():,}"
)


if len(contratos_largo) != 2241:

    print(
        "\nAVISO: se esperaban 2,241 participaciones "
        "RUC-proyecto."
    )


# ============================================================
# 8. CONSTRUIR RELACIONES RUC-GORE-AÑO
# ============================================================

# Una arista representa la existencia de una relación contractual
# entre una empresa y un GORE durante un año.
#
# Su peso es el número de proyectos en los que participa esa
# empresa con dicho GORE durante ese año.

relaciones = (
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
        n_contratos_relacion=(
            "id",
            "nunique"
        )
    )
)


relaciones["n_contratos_relacion"] = (
    relaciones["n_contratos_relacion"]
    .astype("Int64")
)


print(
    f"Relaciones RUC-GORE-año: "
    f"{len(relaciones):,}"
)


# ============================================================
# 9. WEIGHTED DEGREE / STRENGTH
# ============================================================

# Suma del peso de todas las aristas de una empresa
# durante un año.
#
# Equivale al número total de participaciones contractuales
# de la empresa durante ese año.

metricas_empresa_anio = (
    relaciones
    .groupby(
        [
            "ruc",
            "anio"
        ],
        as_index=False
    )
    .agg(
        weighted_degree=(
            "n_contratos_relacion",
            "sum"
        )
    )
)


relaciones = relaciones.merge(
    metricas_empresa_anio,
    on=[
        "ruc",
        "anio"
    ],
    how="left",
    validate="many_to_one"
)


# ============================================================
# 10. DEPENDENCIA EMPRESA -> GORE
# ============================================================

# Proporción de las contrataciones anuales de la empresa
# que corresponden a ese GORE.
#
# Valor 1 = todas las contrataciones de la empresa durante
# ese año fueron con ese GORE.

relaciones["dependencia_empresa_gore"] = (
    relaciones["n_contratos_relacion"]
    /
    relaciones["weighted_degree"]
)


# ============================================================
# 11. TOTAL DE PARTICIPACIONES POR GORE-AÑO
# ============================================================

# Al trabajar con una red empresa-GORE, cuando un mismo proyecto
# contiene varias empresas, cada empresa constituye una
# participación propia en la red.

total_gore_anio = (
    relaciones
    .groupby(
        [
            "anio",
            "gore"
        ],
        as_index=False
    )
    .agg(
        total_participaciones_gore=(
            "n_contratos_relacion",
            "sum"
        )
    )
)


relaciones = relaciones.merge(
    total_gore_anio,
    on=[
        "anio",
        "gore"
    ],
    how="left",
    validate="many_to_one"
)


# ============================================================
# 12. DEPENDENCIA GORE -> EMPRESA
# ============================================================

# Participación de una empresa dentro del total de
# participaciones contractuales del GORE en ese año.

relaciones["dependencia_gore_empresa"] = (
    relaciones["n_contratos_relacion"]
    /
    relaciones["total_participaciones_gore"]
)


# ============================================================
# 13. HHI Y SUPPLIER SHARE POR GORE-AÑO
# ============================================================

# Share de cada empresa dentro del GORE-año.

relaciones["share_empresa_gore"] = (
    relaciones["dependencia_gore_empresa"]
)


relaciones["share_cuadrado"] = (
    relaciones["share_empresa_gore"] ** 2
)


metricas_gore_anio = (
    relaciones
    .groupby(
        [
            "anio",
            "gore"
        ],
        as_index=False
    )
    .agg(
        # HHI:
        # suma de los cuadrados de las participaciones
        # de todas las empresas del GORE.
        hhi_gore=(
            "share_cuadrado",
            "sum"
        ),

        # Supplier share:
        # participación de la empresa con mayor peso
        # contractual dentro del GORE.
        supplier_share_gore=(
            "share_empresa_gore",
            "max"
        )
    )
)


# ============================================================
# 14. DURACIÓN DEL VÍNCULO EMPRESA-GORE
# ============================================================

# Número de años observados en los que aparece la relación
# entre una misma empresa y un mismo GORE.
#
# Períodos observados:
# 2021, 2022 y 2024.
#
# Valores posibles:
# 1, 2 o 3.
#
# Importante:
# 3 no significa necesariamente tres años consecutivos,
# sino presencia en los tres períodos observados.

duracion_vinculo = (
    relaciones
    .groupby(
        [
            "ruc",
            "gore"
        ],
        as_index=False
    )
    .agg(
        duracion_vinculo=(
            "anio",
            "nunique"
        )
    )
)


# ============================================================
# 15. NÚMERO TOTAL DE GORES ATENDIDOS
# ============================================================

# A diferencia de degree_centrality, esta variable mide
# alcance territorial acumulado durante TODO el período
# 2021, 2022 y 2024.
#
# No se reinicia cada año.

gores_periodo = (
    relaciones
    .groupby(
        "ruc",
        as_index=False
    )
    .agg(
        n_gores_atendidos=(
            "gore",
            "nunique"
        )
    )
)


# ============================================================
# 16. CENTRALIDADES DE RED POR AÑO
# ============================================================

centralidades = []


for anio in ANIOS_ANALISIS:

    relaciones_anio = relaciones[
        relaciones["anio"] == anio
    ].copy()


    G = nx.Graph()


    empresas_anio = sorted(
        relaciones_anio["ruc"]
        .dropna()
        .unique()
    )


    gores_anio = sorted(
        relaciones_anio["gore"]
        .dropna()
        .unique()
    )


    nodos_empresa = set()


    # --------------------------------------------------------
    # NODOS EMPRESA
    # --------------------------------------------------------

    for ruc in empresas_anio:

        nodo = f"EMPRESA::{ruc}"

        G.add_node(
            nodo,
            bipartite=0
        )

        nodos_empresa.add(
            nodo
        )


    # --------------------------------------------------------
    # NODOS GORE
    # --------------------------------------------------------

    for gore in gores_anio:

        nodo = f"GORE::{gore}"

        G.add_node(
            nodo,
            bipartite=1
        )


    # --------------------------------------------------------
    # ARISTAS
    # --------------------------------------------------------

    for _, fila in relaciones_anio.iterrows():

        nodo_empresa = (
            f"EMPRESA::{fila['ruc']}"
        )

        nodo_gore = (
            f"GORE::{fila['gore']}"
        )

        G.add_edge(
            nodo_empresa,
            nodo_gore,
            weight=int(
                fila["n_contratos_relacion"]
            )
        )


    # --------------------------------------------------------
    # DEGREE CENTRALITY
    # --------------------------------------------------------

    # Para una empresa:
    #
    # número de GORE conectados
    # --------------------------
    # número de GORE presentes
    # en la red de ese año

    degree_dict = (
        bipartite.degree_centrality(
            G,
            nodos_empresa
        )
    )


    # --------------------------------------------------------
    # CLOSENESS CENTRALITY
    # --------------------------------------------------------

    # Se utiliza la closeness convencional de NetworkX.
    #
    # Mide qué tan cerca se encuentra el nodo del resto
    # de actores alcanzables de la red a partir de las
    # distancias geodésicas.
    #
    # NetworkX aplica corrección para componentes
    # desconectados mediante wf_improved=True.

    closeness_dict = (
        nx.closeness_centrality(
            G,
            wf_improved=True
        )
    )


    for ruc in empresas_anio:

        nodo = (
            f"EMPRESA::{ruc}"
        )

        centralidades.append(
            {
                "ruc": ruc,
                "anio": anio,
                "degree_centrality": (
                    degree_dict.get(
                        nodo
                    )
                ),
                "closeness_centrality": (
                    closeness_dict.get(
                        nodo
                    )
                )
            }
        )


    print(
        f"Año {anio}: "
        f"{len(empresas_anio):,} empresas, "
        f"{len(gores_anio):,} GORE, "
        f"{G.number_of_edges():,} vínculos"
    )


centralidades = pd.DataFrame(
    centralidades
)


# ============================================================
# 17. CONSOLIDAR TODAS LAS MÉTRICAS
# ============================================================

metricas = relaciones.merge(
    centralidades,
    on=[
        "ruc",
        "anio"
    ],
    how="left",
    validate="many_to_one"
)


metricas = metricas.merge(
    metricas_gore_anio,
    on=[
        "anio",
        "gore"
    ],
    how="left",
    validate="many_to_one"
)


metricas = metricas.merge(
    duracion_vinculo,
    on=[
        "ruc",
        "gore"
    ],
    how="left",
    validate="many_to_one"
)


metricas = metricas.merge(
    gores_periodo,
    on="ruc",
    how="left",
    validate="many_to_one"
)


# ============================================================
# 18. TIPOS DE DATOS
# ============================================================

columnas_enteras = [
    "anio",
    "n_contratos_relacion",
    "weighted_degree",
    "total_participaciones_gore",
    "duracion_vinculo",
    "n_gores_atendidos"
]


for columna in columnas_enteras:

    metricas[columna] = pd.to_numeric(
        metricas[columna],
        errors="coerce"
    ).astype("Int64")


columnas_decimales = [
    "degree_centrality",
    "closeness_centrality",
    "hhi_gore",
    "supplier_share_gore",
    "dependencia_empresa_gore",
    "dependencia_gore_empresa"
]


for columna in columnas_decimales:

    metricas[columna] = pd.to_numeric(
        metricas[columna],
        errors="coerce"
    )


# ============================================================
# 19. ORDEN FINAL DE LA TABLA DE MÉTRICAS
# ============================================================

metricas = metricas[
    [
        "ruc",
        "anio",
        "gore",

        # Control de la relación
        "n_contratos_relacion",

        # Posición estructural
        "degree_centrality",
        "weighted_degree",
        "closeness_centrality",

        # Concentración del GORE
        "hhi_gore",
        "supplier_share_gore",

        # Dependencias bilaterales
        "dependencia_empresa_gore",
        "dependencia_gore_empresa",

        # Persistencia
        "duracion_vinculo",

        # Alcance territorial total
        "n_gores_atendidos"
    ]
].copy()


metricas = (
    metricas
    .sort_values(
        [
            "anio",
            "gore",
            "ruc"
        ]
    )
    .reset_index(drop=True)
)


# ============================================================
# 20. VALIDACIONES ESTRUCTURALES
# ============================================================

print("\n" + "=" * 78)
print("VALIDACIÓN DE MÉTRICAS")
print("=" * 78)


# ------------------------------------------------------------
# 20.1 DUPLICADOS
# ------------------------------------------------------------

duplicados = (
    metricas
    .duplicated(
        subset=[
            "ruc",
            "anio",
            "gore"
        ]
    )
    .sum()
)


print(
    f"Duplicados RUC-año-GORE: "
    f"{duplicados:,}"
)


if duplicados > 0:

    raise ValueError(
        "ERROR: existen duplicados RUC-año-GORE."
    )


# ------------------------------------------------------------
# 20.2 VARIABLES ENTRE 0 Y 1
# ------------------------------------------------------------

variables_01 = [
    "degree_centrality",
    "closeness_centrality",
    "hhi_gore",
    "supplier_share_gore",
    "dependencia_empresa_gore",
    "dependencia_gore_empresa"
]


for columna in variables_01:

    fuera_rango = (
        (
            metricas[columna] < 0
        )
        |
        (
            metricas[columna] > 1
        )
    ).sum()


    print(
        f"{columna} fuera de [0,1]: "
        f"{fuera_rango:,}"
    )


    if fuera_rango > 0:

        raise ValueError(
            f"ERROR: {columna} tiene valores fuera de rango."
        )


# ------------------------------------------------------------
# 20.3 DURACIÓN DEL VÍNCULO
# ------------------------------------------------------------

duracion_invalida = (
    (
        metricas["duracion_vinculo"] < 1
    )
    |
    (
        metricas["duracion_vinculo"] > 3
    )
).sum()


print(
    f"Duración de vínculo fuera de 1-3: "
    f"{duracion_invalida:,}"
)


if duracion_invalida > 0:

    raise ValueError(
        "ERROR: duración de vínculo inválida."
    )


# ------------------------------------------------------------
# 20.4 ALCANCE TERRITORIAL
# ------------------------------------------------------------

gores_invalidos = (
    metricas["n_gores_atendidos"] < 1
).sum()


print(
    f"n_gores_atendidos < 1: "
    f"{gores_invalidos:,}"
)


if gores_invalidos > 0:

    raise ValueError(
        "ERROR: existen valores inválidos "
        "en n_gores_atendidos."
    )


# ============================================================
# 21. VALIDACIONES DE PROPORCIONES
# ============================================================

# Para cada empresa-año, la suma de dependencia empresa->GORE
# debe ser exactamente 1.

control_dependencia_empresa = (
    metricas
    .groupby(
        [
            "ruc",
            "anio"
        ]
    )["dependencia_empresa_gore"]
    .sum()
)


errores_dep_empresa = (
    (
        control_dependencia_empresa
        - 1
    )
    .abs()
    > 1e-10
).sum()


print(
    "Empresa-año cuya dependencia empresa->GORE "
    f"no suma 1: {errores_dep_empresa:,}"
)


if errores_dep_empresa > 0:

    raise ValueError(
        "ERROR en dependencia_empresa_gore."
    )


# Para cada GORE-año, la suma de dependencia GORE->empresa
# debe ser exactamente 1.

control_dependencia_gore = (
    metricas
    .groupby(
        [
            "anio",
            "gore"
        ]
    )["dependencia_gore_empresa"]
    .sum()
)


errores_dep_gore = (
    (
        control_dependencia_gore
        - 1
    )
    .abs()
    > 1e-10
).sum()


print(
    "GORE-año cuya dependencia GORE->empresa "
    f"no suma 1: {errores_dep_gore:,}"
)


if errores_dep_gore > 0:

    raise ValueError(
        "ERROR en dependencia_gore_empresa."
    )


# ============================================================
# 22. VALORES FALTANTES
# ============================================================

print("\nValores faltantes:")


print(
    metricas[
        METRICAS_RED
    ]
    .isna()
    .sum()
    .to_string()
)


if (
    metricas[
        METRICAS_RED
    ]
    .isna()
    .sum()
    .sum()
    > 0
):

    raise ValueError(
        "ERROR: existen valores faltantes "
        "en las métricas de red."
    )


# ============================================================
# 23. GUARDAR TABLA DE MÉTRICAS
# ============================================================

metricas.to_csv(
    SALIDA_METRICAS,
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 24. CREAR LOOKUP PARA LOS OBJETOS RUC
# ============================================================

lookup_metricas = {}


for _, fila in metricas.iterrows():

    clave = (
        str(fila["ruc"]),
        int(fila["anio"]),
        normalizar_gore(
            fila["gore"]
        )
    )


    lookup_metricas[clave] = {
        metrica: valor_json(
            fila[metrica]
        )
        for metrica in METRICAS_RED
    }


# ============================================================
# 25. LEER ARCHIVO ENRIQUECIDO DEL SCRIPT 06
# ============================================================

enriquecido = pd.read_csv(
    ARCHIVO_ENRIQUECIDO,
    dtype=str,
    encoding="utf-8-sig",
    low_memory=False
)


enriquecido["fecha_dt"] = pd.to_datetime(
    enriquecido["fecha"],
    format="%d/%m/%Y",
    errors="coerce"
)


enriquecido["anio"] = (
    enriquecido["fecha_dt"]
    .dt.year
    .astype("Int64")
)


if enriquecido["anio"].isna().any():

    raise ValueError(
        "ERROR: existen fechas inválidas "
        "en el archivo enriquecido."
    )


enriquecido["gore"] = (
    enriquecido["gore"]
    .apply(normalizar_gore)
)


# ============================================================
# 26. INSERTAR MÉTRICAS DENTRO DE ruc1...ruc9
# ============================================================

for columna in COLUMNAS_RUC:

    enriquecido[columna] = enriquecido.apply(
        lambda fila: enriquecer_objeto_ruc(
            fila[columna],
            fila["anio"],
            fila["gore"],
            lookup_metricas
        ),
        axis=1
    )


# ============================================================
# 27. ELIMINAR COLUMNAS AUXILIARES
# ============================================================

enriquecido = enriquecido.drop(
    columns=[
        "fecha_dt",
        "anio"
    ]
)


# ============================================================
# 28. VALIDAR PROYECTOS
# ============================================================

if len(enriquecido) != 1222:

    raise ValueError(
        "ERROR: cambió el número de proyectos."
    )


if enriquecido["id"].nunique() != 1222:

    raise ValueError(
        "ERROR: los IDs de proyecto dejaron de ser únicos."
    )


# ============================================================
# 29. GUARDAR CONTRATACIONES CON MÉTRICAS DE RED
# ============================================================

enriquecido.to_csv(
    SALIDA_ENRIQUECIDA_RED,
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 30. RESUMEN FINAL
# ============================================================

print("\n" + "=" * 78)
print("MÉTRICAS DE RED GENERADAS")
print("=" * 78)


print(
    f"Filas RUC-GORE-año: "
    f"{len(metricas):,}"
)

print(
    f"RUC distintos: "
    f"{metricas['ruc'].nunique():,}"
)


print("\nRangos principales:")


print(
    f"Degree centrality: "
    f"{metricas['degree_centrality'].min():.4f} - "
    f"{metricas['degree_centrality'].max():.4f}"
)


print(
    f"Weighted degree: "
    f"{metricas['weighted_degree'].min()} - "
    f"{metricas['weighted_degree'].max()}"
)


print(
    f"Closeness centrality: "
    f"{metricas['closeness_centrality'].min():.4f} - "
    f"{metricas['closeness_centrality'].max():.4f}"
)


print(
    f"HHI GORE: "
    f"{metricas['hhi_gore'].min():.4f} - "
    f"{metricas['hhi_gore'].max():.4f}"
)


print(
    f"Supplier share GORE: "
    f"{metricas['supplier_share_gore'].min():.4f} - "
    f"{metricas['supplier_share_gore'].max():.4f}"
)


print(
    f"Dependencia empresa->GORE: "
    f"{metricas['dependencia_empresa_gore'].min():.4f} - "
    f"{metricas['dependencia_empresa_gore'].max():.4f}"
)


print(
    f"Dependencia GORE->empresa: "
    f"{metricas['dependencia_gore_empresa'].min():.4f} - "
    f"{metricas['dependencia_gore_empresa'].max():.4f}"
)


print(
    f"Duración vínculo: "
    f"{metricas['duracion_vinculo'].min()} - "
    f"{metricas['duracion_vinculo'].max()}"
)


print(
    f"GORE atendidos en todo el período: "
    f"{metricas['n_gores_atendidos'].min()} - "
    f"{metricas['n_gores_atendidos'].max()}"
)


print("\nArchivos generados:")

print(
    f"1. {SALIDA_METRICAS}"
)

print(
    f"2. {SALIDA_ENRIQUECIDA_RED}"
)