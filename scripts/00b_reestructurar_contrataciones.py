from pathlib import Path
import pandas as pd


# ============================================================
# 1. RUTAS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

ARCHIVO_ORIGINAL = (
    BASE_DIR
    / "data"
    / "insumos_originales"
    / "contrataciones_2004_2024.csv"
)

ARCHIVO_SALIDA = (
    BASE_DIR
    / "data"
    / "insumos_originales"
    / "contrataciones_2021_2022_2024.csv"
)


# ============================================================
# 2. AÑOS OBJETIVO
# ============================================================

ANIOS_OBJETIVO = [
    2021,
    2022,
    2024
]


# ============================================================
# 3. LEER ARCHIVO
# ============================================================

df = pd.read_csv(
    ARCHIVO_ORIGINAL,
    dtype=str,
    encoding="utf-8-sig"
)

print(f"Filas originales: {len(df):,}")


# ============================================================
# 4. CONVERTIR FECHA Y OBTENER AÑO
# ============================================================

df["_fecha_dt"] = pd.to_datetime(
    df["fecha"],
    format="%d/%m/%Y",
    errors="coerce"
)

df["_anio"] = df["_fecha_dt"].dt.year


# ============================================================
# 5. FILTRAR
# ============================================================

df_filtrado = df[
    df["_anio"].isin(ANIOS_OBJETIVO)
].copy()


print(
    f"Filas 2021/2022/2024: "
    f"{len(df_filtrado):,}"
)

print("\nContrataciones por año:")

print(
    df_filtrado["_anio"]
    .value_counts()
    .sort_index()
    .to_string()
)


# ============================================================
# 6. ELIMINAR COLUMNAS AUXILIARES
# ============================================================

df_filtrado = df_filtrado.drop(
    columns=[
        "_fecha_dt",
        "_anio"
    ]
)


# ============================================================
# 7. VALIDAR IDS
# ============================================================

if df_filtrado["id"].duplicated().any():
    raise ValueError(
        "ERROR: existen IDs duplicados."
    )

print(
    f"\nIDs únicos finales: "
    f"{df_filtrado['id'].nunique():,}"
)


# ============================================================
# 8. GUARDAR NUEVO ARCHIVO
# ============================================================

df_filtrado.to_csv(
    ARCHIVO_SALIDA,
    index=False,
    encoding="utf-8-sig"
)


print("\nArchivo generado correctamente:")
print(ARCHIVO_SALIDA)