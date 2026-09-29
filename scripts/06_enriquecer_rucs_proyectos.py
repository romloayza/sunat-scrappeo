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

ARCHIVO_CONTRATOS = (
    INSUMOS_DIR / "contrataciones_2021_2022_2024.csv"
)

ARCHIVO_EMPRESAS = (
    DATA_DIR / "data_final_consolidada.csv"
)

SALIDA = (
    INTERMEDIATE_DIR
    / "contrataciones_2021_2022_2024_enriquecida.csv"
)


# ============================================================
# 2. CONFIGURACIÓN
# ============================================================

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

ATRIBUTOS = [
    "antiguedad_empresa",
    "cmc",
    "cantidad_rubros",
    "actividad_principal",
    "penalidades_acum",
    "sanciones_tcp_acum",
    "estado",
    "condicion"
]


# ============================================================
# 3. FUNCIONES
# ============================================================

def limpiar_ruc(valor):
    """
    Limpia valores de RUC y convierte vacíos/NaN a None.
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


def valor_json(valor):
    """
    Convierte valores pandas/numpy a valores compatibles con JSON.
    """

    if pd.isna(valor):
        return None

    if hasattr(valor, "item"):
        try:
            return valor.item()
        except Exception:
            pass

    return valor


def crear_objeto_ruc(ruc, anio, lookup):
    """
    Construye el objeto JSON que irá dentro de cada celda ruc1...ruc9.
    """

    if ruc is None or pd.isna(ruc):
        return None

    clave = (
        str(ruc),
        int(anio)
    )

    datos = lookup.get(clave)

    if datos is None:

        objeto = {
            "ruc": ruc,
            "antiguedad_empresa": None,
            "cmc": None,
            "cantidad_rubros": None,
            "actividad_principal": None,
            "penalidades_acum": None,
            "sanciones_tcp_acum": None,
            "estado": None,
            "condicion": None
        }

    else:

        objeto = {
            "ruc": ruc,
            "antiguedad_empresa": valor_json(
                datos["antiguedad_empresa"]
            ),
            "cmc": valor_json(
                datos["cmc"]
            ),
            "cantidad_rubros": valor_json(
                datos["cantidad_rubros"]
            ),
            "actividad_principal": valor_json(
                datos["actividad_principal"]
            ),
            "penalidades_acum": valor_json(
                datos["penalidades_acum"]
            ),
            "sanciones_tcp_acum": valor_json(
                datos["sanciones_tcp_acum"]
            ),
            "estado": valor_json(
                datos["estado"]
            ),
            "condicion": valor_json(
                datos["condicion"]
            )
        }

    return json.dumps(
        objeto,
        ensure_ascii=False,
        separators=(",", ":")
    )


# ============================================================
# 4. CARGAR CONTRATACIONES
# ============================================================

contratos = pd.read_csv(
    ARCHIVO_CONTRATOS,
    dtype=str,
    encoding="utf-8-sig"
)


print("\n" + "=" * 75)
print("CONTRATACIONES")
print("=" * 75)

print(
    f"Proyectos: "
    f"{len(contratos):,}"
)

print(
    f"IDs únicos: "
    f"{contratos['id'].nunique():,}"
)


# ============================================================
# 5. CREAR AÑO DEL PROYECTO
# ============================================================

contratos["_fecha_dt"] = pd.to_datetime(
    contratos["fecha"],
    format="%d/%m/%Y",
    errors="coerce"
)


contratos["_anio"] = (
    contratos["_fecha_dt"]
    .dt.year
    .astype("Int64")
)


if contratos["_anio"].isna().any():

    raise ValueError(
        "ERROR: existen proyectos cuya fecha no pudo convertirse."
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
# 7. CARGAR DATA FINAL CONSOLIDADA
# ============================================================

empresas = pd.read_csv(
    ARCHIVO_EMPRESAS,
    dtype={
        "ruc": str
    },
    encoding="utf-8-sig",
    low_memory=False
)


empresas["ruc"] = (
    empresas["ruc"]
    .apply(limpiar_ruc)
)


empresas["anio"] = pd.to_numeric(
    empresas["anio"],
    errors="coerce"
).astype("Int64")


print("\n" + "=" * 75)
print("DATA FINAL CONSOLIDADA")
print("=" * 75)

print(
    f"Filas: "
    f"{len(empresas):,}"
)

print(
    f"RUC distintos: "
    f"{empresas['ruc'].nunique():,}"
)


# ============================================================
# 8. VALIDAR CONSISTENCIA RUC-AÑO
# ============================================================

conflictos = []


for atributo in ATRIBUTOS:

    control = (
        empresas
        .groupby(
            [
                "ruc",
                "anio"
            ]
        )[atributo]
        .nunique(
            dropna=True
        )
    )

    n_conflictos = (
        control > 1
    ).sum()

    if n_conflictos > 0:

        conflictos.append(
            (
                atributo,
                n_conflictos
            )
        )


if conflictos:

    print("\nSe encontraron inconsistencias:")

    for atributo, n in conflictos:

        print(
            f"{atributo}: "
            f"{n:,} RUC-año con más de un valor"
        )

    raise ValueError(
        "Existen atributos distintos para el mismo RUC-año."
    )


print(
    "\nConsistencia RUC-año: OK"
)


# ============================================================
# 9. CREAR TABLA ÚNICA RUC-AÑO
# ============================================================

empresa_anio = (
    empresas[
        [
            "ruc",
            "anio"
        ]
        + ATRIBUTOS
    ]
    .drop_duplicates(
        subset=[
            "ruc",
            "anio"
        ]
    )
    .copy()
)


print(
    f"RUC-año únicos disponibles: "
    f"{len(empresa_anio):,}"
)


# ============================================================
# 10. CREAR LOOKUP
# ============================================================

lookup = {}


for _, fila in empresa_anio.iterrows():

    clave = (
        str(fila["ruc"]),
        int(fila["anio"])
    )

    lookup[clave] = fila.to_dict()


# ============================================================
# 11. CONTAR PARTICIPACIONES REALES
# ============================================================

total_rucs = 0
rucs_sin_match = set()


for columna in COLUMNAS_RUC:

    for _, fila in contratos[
        [
            columna,
            "_anio"
        ]
    ].iterrows():

        ruc = fila[columna]

        if ruc is None or pd.isna(ruc):
            continue

        total_rucs += 1

        clave = (
            ruc,
            int(fila["_anio"])
        )

        if clave not in lookup:

            rucs_sin_match.add(
                clave
            )


print("\n" + "=" * 75)
print("COBERTURA DE EMPRESAS")
print("=" * 75)

print(
    f"Participaciones RUC-proyecto: "
    f"{total_rucs:,}"
)

print(
    f"RUC-año sin información consolidada: "
    f"{len(rucs_sin_match):,}"
)


if len(rucs_sin_match) > 0:

    print("\nRUC-año sin match:")

    for ruc, anio in sorted(rucs_sin_match):
        print(
            f"{ruc} - {anio}"
        )


# ============================================================
# 12. ENRIQUECER ruc1 ... ruc9
# ============================================================

for columna in COLUMNAS_RUC:

    contratos[columna] = contratos.apply(
        lambda fila: crear_objeto_ruc(
            fila[columna],
            fila["_anio"],
            lookup
        ),
        axis=1
    )


# ============================================================
# 13. ELIMINAR COLUMNAS AUXILIARES
# ============================================================

contratos = contratos.drop(
    columns=[
        "_fecha_dt",
        "_anio"
    ]
)


# ============================================================
# 14. ORDEN FINAL
# ============================================================

columnas_finales = [
    "id",
    "gore",
    "monto",
    "fecha",
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


contratos = contratos[
    columnas_finales
]


# ============================================================
# 15. VALIDACIONES FINALES
# ============================================================

if contratos["id"].duplicated().any():

    raise ValueError(
        "ERROR: existen IDs de proyecto duplicados."
    )


if len(contratos) != 1222:

    print(
        "\nAVISO: el archivo no contiene exactamente "
        "1,222 proyectos."
    )


# ============================================================
# 16. GUARDAR
# ============================================================

contratos.to_csv(
    SALIDA,
    index=False,
    encoding="utf-8-sig"
)


# ============================================================
# 17. RESUMEN FINAL
# ============================================================

print("\n" + "=" * 75)
print("ARCHIVO GENERADO")
print("=" * 75)

print(
    f"Proyectos finales: "
    f"{len(contratos):,}"
)

print(
    f"IDs únicos: "
    f"{contratos['id'].nunique():,}"
)

print(
    f"Participaciones RUC-proyecto: "
    f"{total_rucs:,}"
)

print(
    f"RUC-año sin match: "
    f"{len(rucs_sin_match):,}"
)

print("\nSalida:")

print(
    SALIDA
)