import asyncio
import csv
import json
import httpx

# ---------- CONFIGURA ESTO ----------
INPUT_JSON = "data/rucs.json"
RUC_COLUMN = "RUC"              # <-- cambia esto al nombre real de la columna en tu CSV
OUTPUT_JSON = "data/resultados_rucs.json"
CONCURRENCIA_MAXIMA = 5         # cuántas peticiones en simultáneo (súbelo/bájalo según cómo responda SUNAT)
DELAY_SEGUNDOS = 0.5            # pausa por petición para no saturar el servidor
GUARDAR_CADA = 50               # guarda progreso cada N resultados (por si se corta el proceso)

TOKEN = "ivo4zbzeq24890kz9pa7gwjb4k1hti0raycm8h2obk61bt69u8vj"
URL = "https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/jcrS00Alias"
HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "accept-language": "es,es-ES;q=0.9,en;q=0.8",
    "content-type": "application/x-www-form-urlencoded",
    "referer": "https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/FrameCriterioBusquedaWeb.jsp",
}
# -------------------------------------


def leer_rucs_json(path: str) -> list[str]:
    """Lee los RUC desde un archivo JSON."""

    with open(path, "r", encoding="utf-8") as f:
        datos = json.load(f)

    rucs = []

    # Formato:
    # ["20604434972", "20600340230", ...]
    if isinstance(datos, list):

        for item in datos:

            if isinstance(item, (str, int)):
                ruc = str(item).strip()

            elif isinstance(item, dict):
                ruc = str(
                    item.get("RUC")
                    or item.get("ruc")
                    or ""
                ).strip()

            else:
                continue

            if ruc:
                rucs.append(ruc)

    # También acepta:
    # {"rucs": [...]}
    elif isinstance(datos, dict):

        lista = datos.get("rucs", [])

        for item in lista:

            if isinstance(item, (str, int)):
                ruc = str(item).strip()

            elif isinstance(item, dict):
                ruc = str(
                    item.get("RUC")
                    or item.get("ruc")
                    or ""
                ).strip()

            else:
                continue

            if ruc:
                rucs.append(ruc)

    # quitar duplicados
    return list(dict.fromkeys(rucs))


async def consultar_ruc(client: httpx.AsyncClient, ruc: str, semaforo: asyncio.Semaphore) -> dict:
    async with semaforo:
        data = {
            "accion": "consPorRuc",
            "razSoc": "",
            "nroRuc": ruc,
            "nrodoc": "",
            "token": TOKEN,
            "contexto": "ti-it",
            "modo": "1",
            "rbtnTipo": "1",
            "search1": ruc,
            "tipdoc": "1",
            "search2": "",
            "search3": "",
            "codigo": "",
        }
        try:
            resp = await client.post(URL, headers=HEADERS, data=data)
            resp.raise_for_status()
            return {"ruc": ruc, "html": resp.text, "ok": True}
        except Exception as e:
            return {"ruc": ruc, "error": str(e), "ok": False}
        finally:
            await asyncio.sleep(DELAY_SEGUNDOS)


def guardar(resultados: list[dict]) -> None:
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)


async def main():
    rucs = leer_rucs_json(INPUT_JSON)
    print(f"RUCs a consultar: {len(rucs)}")

    semaforo = asyncio.Semaphore(CONCURRENCIA_MAXIMA)
    resultados = []

    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        tareas = [asyncio.create_task(consultar_ruc(client, ruc, semaforo)) for ruc in rucs]
        for i, tarea in enumerate(asyncio.as_completed(tareas), start=1):
            resultado = await tarea
            resultados.append(resultado)
            if i % GUARDAR_CADA == 0:
                print(f"Progreso: {i}/{len(rucs)}")
                guardar(resultados)

    guardar(resultados)
    print(f"Listo. Resultados guardados en {OUTPUT_JSON}")


if __name__ == "__main__":
    asyncio.run(main())