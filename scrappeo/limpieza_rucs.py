from pathlib import Path
import csv
import json
import re
from datetime import datetime

# ============================================================
# CONFIGURACIÓN
# ============================================================

INPUT_FILE = Path("data") / "contrataciones_2004_2024.csv"
OUTPUT_FILE = Path("data") / "rucs_2021_2022_2024.json"

ANIOS_OBJETIVO = {2021, 2022, 2024}

# ============================================================
# FUNCIÓN PARA LIMPIAR RUC
# ============================================================

def limpiar_ruc(valor):
    if valor is None:
        return None

    valor = str(valor).strip()

    if not valor or valor.lower() == "nan":
        return None

    # Quitar .0 al final si vino de Excel
    valor = re.sub(r"\.0$", "", valor)

    # Dejar solo dígitos
    valor = re.sub(r"\D", "", valor)

    # RUC peruano = 11 dígitos
    if len(valor) != 11:
        return None

    return valor

# ============================================================
# LEER CSV Y EXTRAER RUC DE 2021, 2022 O 2024
# ============================================================

rucs_validos = set()
filas_procesadas = 0

with open(INPUT_FILE, "r", encoding="utf-8-sig", newline="") as archivo:
    muestra = archivo.read(5000)
    archivo.seek(0)

    try:
        dialecto = csv.Sniffer().sniff(muestra)
    except csv.Error:
        dialecto = csv.excel

    lector = csv.DictReader(archivo, dialect=dialecto)

    # Normalizar nombres de columnas
    lector.fieldnames = [col.strip().upper() for col in lector.fieldnames]

    columnas_empresas = [
        col for col in lector.fieldnames
        if col.startswith("EMPRESA_")
    ]

    for fila in lector:
        filas_procesadas += 1

        # Normalizar claves de la fila
        fila = {k.strip().upper(): v for k, v in fila.items()}

        fecha_texto = str(fila.get("FECHA", "")).strip()

        if not fecha_texto:
            continue

        try:
            fecha = datetime.strptime(fecha_texto, "%d/%m/%Y")
        except ValueError:
            continue

        anio = fecha.year

        # Solo considerar filas de 2021, 2022 o 2024
        if anio not in ANIOS_OBJETIVO:
            continue

        for columna in columnas_empresas:
            ruc = limpiar_ruc(fila.get(columna))
            if ruc:
                rucs_validos.add(ruc)

# ============================================================
# ORDENAR Y GUARDAR JSON
# ============================================================

rucs_validos = sorted(rucs_validos)

with open(OUTPUT_FILE, "w", encoding="utf-8") as archivo:
    json.dump(rucs_validos, archivo, ensure_ascii=False, indent=2)

# ============================================================
# RESULTADO
# ============================================================

print(f"Filas procesadas: {filas_procesadas:,}")
print(f"RUC encontrados en 2021, 2022 o 2024: {len(rucs_validos):,}")
print(f"Archivo guardado en: {OUTPUT_FILE}")