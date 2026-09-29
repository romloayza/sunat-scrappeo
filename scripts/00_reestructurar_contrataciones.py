from pathlib import Path
import pandas as pd


# ============================================================
# 1. RUTAS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

ARCHIVO = (
    BASE_DIR
    / "data"
    / "insumos_originales"
    / "contrataciones_2004_2024.csv"
)


# ============================================================
# 2. LEER ARCHIVO
# ============================================================

df = pd.read_csv(
    ARCHIVO,
    dtype=str,
    encoding="utf-8-sig"
)

print(f"Filas originales: {len(df):,}")


# ============================================================
# 3. CREAR ID
# ============================================================

df.insert(
    0,
    "id",
    range(1, len(df) + 1)
)


# ============================================================
# 4. RENOMBRAR COLUMNAS
# ============================================================

df = df.rename(
    columns={
        "DEPARTAMENTO": "gore",
        "MONTO": "monto",
        "FECHA": "fecha",
        "EMPRESA_1": "ruc1",
        "EMPRESA_2": "ruc2",
        "EMPRESA_3": "ruc3",
        "EMPRESA_4": "ruc4",
        "EMPRESA_5": "ruc5",
        "EMPRESA_6": "ruc6",
        "EMPRESA_7": "ruc7",
        "EMPRESA_8": "ruc8",
        "EMPRESA_9": "ruc9",
    }
)


# ============================================================
# 5. ORDENAR COLUMNAS
# ============================================================

columnas = [
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
    "ruc9",
]

df = df[columnas]


# ============================================================
# 6. VALIDACIONES
# ============================================================

if df["id"].duplicated().any():
    raise ValueError("ERROR: existen IDs duplicados.")

if df["id"].isna().any():
    raise ValueError("ERROR: existen IDs vacíos.")

print(f"IDs únicos: {df['id'].nunique():,}")
print(f"Filas finales: {len(df):,}")


# ============================================================
# 7. SOBRESCRIBIR ARCHIVO
# ============================================================

df.to_csv(
    ARCHIVO,
    index=False,
    encoding="utf-8-sig"
)

print("\nArchivo actualizado correctamente:")
print(ARCHIVO)