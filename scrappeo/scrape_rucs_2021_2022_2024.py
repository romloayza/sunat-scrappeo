import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright


# ==========================================================
# CONFIGURACIÓN
# ==========================================================

INPUT_JSON = "data/rucs_2021_2022_2024.json"

OUTPUT_JSON = "data/resultados_rucs_2021_2022_2024.json"

URL_INICIO = (
    "https://e-consultaruc.sunat.gob.pe/"
    "cl-ti-itmrconsruc/FrameCriterioBusquedaWeb.jsp"
)

# Pausa entre cada consulta.
# No recomiendo bajarlo demasiado.
DELAY_SEGUNDOS = 2.0

# Número de intentos por RUC si algo falla.
MAX_INTENTOS = 2

# False = verás el navegador.
# Para las primeras pruebas recomiendo False.
HEADLESS = False


# ==========================================================
# LEER RUCs
# ==========================================================

def leer_rucs_json(path: str) -> list[str]:
    """
    Lee RUCs desde diferentes estructuras JSON posibles.
    """

    with open(path, "r", encoding="utf-8") as f:
        datos = json.load(f)

    rucs = []

    # Caso:
    # ["20123456789", "20987654321"]
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

    # Caso:
    # {"rucs": [...]}
    elif isinstance(datos, dict):

        lista = (
            datos.get("rucs")
            or datos.get("RUC")
            or datos.get("data")
            or []
        )

        if isinstance(lista, list):

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

    # Quitar duplicados manteniendo orden
    rucs = list(dict.fromkeys(rucs))

    return rucs


# ==========================================================
# GUARDAR / RECUPERAR PROGRESO
# ==========================================================

def guardar_resultados(resultados: list[dict]) -> None:

    Path("data").mkdir(exist_ok=True)

    with open(
        OUTPUT_JSON,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            resultados,
            f,
            ensure_ascii=False,
            indent=2
        )


def cargar_resultados_existentes() -> list[dict]:
    """
    Si ya existe un archivo de resultados, lo carga
    para continuar desde donde quedó.
    """

    path = Path(OUTPUT_JSON)

    if not path.exists():
        return []

    try:

        with open(
            OUTPUT_JSON,
            "r",
            encoding="utf-8"
        ) as f:

            datos = json.load(f)

        if isinstance(datos, list):
            return datos

    except Exception as e:

        print(
            "⚠️ No se pudo leer el archivo de progreso:",
            e
        )

    return []


# ==========================================================
# EXTRAER DATOS DE LA FICHA SUNAT
# ==========================================================

async def extraer_datos(page, ruc_consultado: str) -> dict:

    datos = await page.evaluate(
        """
        () => {

            function limpiar(texto) {

                if (!texto) {
                    return null;
                }

                return texto
                    .replace(/\\s+/g, " ")
                    .trim();
            }


            function buscarHeading(etiqueta) {

                const headings =
                    Array.from(
                        document.querySelectorAll(
                            "h4.list-group-item-heading"
                        )
                    );

                return headings.find(
                    el =>
                        limpiar(el.textContent)
                        === etiqueta
                );
            }


            function valorDespuesDeEtiqueta(etiqueta) {

                const heading =
                    buscarHeading(etiqueta);

                if (!heading) {
                    return null;
                }

                const columna =
                    heading.closest(
                        "[class*='col-']"
                    );

                if (!columna) {
                    return null;
                }

                const siguiente =
                    columna.nextElementSibling;

                if (!siguiente) {
                    return null;
                }

                return limpiar(
                    siguiente.innerText
                );
            }


            function listaDespuesDeEtiqueta(etiqueta) {

                const heading =
                    buscarHeading(etiqueta);

                if (!heading) {
                    return [];
                }

                const columna =
                    heading.closest(
                        "[class*='col-']"
                    );

                if (!columna) {
                    return [];
                }

                const siguiente =
                    columna.nextElementSibling;

                if (!siguiente) {
                    return [];
                }

                const filas =
                    Array.from(
                        siguiente.querySelectorAll(
                            "tr"
                        )
                    );

                if (filas.length > 0) {

                    return filas
                        .map(
                            fila =>
                                limpiar(
                                    fila.innerText
                                )
                        )
                        .filter(Boolean);
                }

                const texto =
                    limpiar(
                        siguiente.innerText
                    );

                return texto
                    ? [texto]
                    : [];
            }


            // ==========================================
            // RUC + RAZÓN SOCIAL
            // ==========================================

            const rucRazon =
                valorDespuesDeEtiqueta(
                    "Número de RUC:"
                );

            let ruc = null;
            let razon_social = null;

            if (rucRazon) {

                const indice =
                    rucRazon.indexOf(" - ");

                if (indice !== -1) {

                    ruc =
                        rucRazon
                            .substring(
                                0,
                                indice
                            )
                            .trim();

                    razon_social =
                        rucRazon
                            .substring(
                                indice + 3
                            )
                            .trim();

                } else {

                    ruc =
                        rucRazon.trim();
                }
            }


            // ==========================================
            // ESTADO
            // ==========================================

            const estadoCompleto =
                valorDespuesDeEtiqueta(
                    "Estado del Contribuyente:"
                );

            let estado = null;
            let fecha_baja = null;

            if (estadoCompleto) {

                estado =
                    estadoCompleto
                        .split(
                            "Fecha de Baja:"
                        )[0]
                        .trim();

                const matchFecha =
                    estadoCompleto.match(
                        /Fecha de Baja:\\s*(\\d{2}\\/\\d{2}\\/\\d{4})/
                    );

                if (matchFecha) {
                    fecha_baja =
                        matchFecha[1];
                }
            }


            // ==========================================
            // CONDICIÓN
            // ==========================================

            const condicionCompleta =
                valorDespuesDeEtiqueta(
                    "Condición del Contribuyente:"
                );

            let condicion = null;

            if (condicionCompleta) {

                condicion =
                    condicionCompleta
                        .split(
                            /Deberá|Debe|Para ello/i
                        )[0]
                        .trim();
            }


            // ==========================================
            // FECHA CONSULTA
            // ==========================================

            let fechaConsulta = null;

            const footer =
                document.querySelector(
                    ".panel-footer"
                );

            if (footer) {

                fechaConsulta =
                    limpiar(
                        footer.innerText
                    );

                if (fechaConsulta) {

                    fechaConsulta =
                        fechaConsulta.replace(
                            /^Fecha consulta:\\s*/i,
                            ""
                        );
                }
            }


            // ==========================================
            // RESULTADO
            // ==========================================

            return {

                ruc: ruc,

                razon_social:
                    razon_social,

                tipo_contribuyente:
                    valorDespuesDeEtiqueta(
                        "Tipo Contribuyente:"
                    ),

                nombre_comercial:
                    valorDespuesDeEtiqueta(
                        "Nombre Comercial:"
                    ),

                fecha_inscripcion:
                    valorDespuesDeEtiqueta(
                        "Fecha de Inscripción:"
                    ),

                fecha_inicio_actividades:
                    valorDespuesDeEtiqueta(
                        "Fecha de Inicio de Actividades:"
                    ),

                estado_contribuyente:
                    estado,

                fecha_baja:
                    fecha_baja,

                condicion_contribuyente:
                    condicion,

                domicilio_fiscal:
                    valorDespuesDeEtiqueta(
                        "Domicilio Fiscal:"
                    ),

                sistema_emision_comprobante:
                    valorDespuesDeEtiqueta(
                        "Sistema Emisión de Comprobante:"
                    ),

                actividad_comercio_exterior:
                    valorDespuesDeEtiqueta(
                        "Actividad Comercio Exterior:"
                    ),

                sistema_contabilidad:
                    valorDespuesDeEtiqueta(
                        "Sistema Contabilidad:"
                    ),

                actividades_economicas:
                    listaDespuesDeEtiqueta(
                        "Actividad(es) Económica(s):"
                    ),

                sistema_emision_electronica:
                    valorDespuesDeEtiqueta(
                        "Sistema de Emisión Electrónica:"
                    ),

                emisor_electronico_desde:
                    valorDespuesDeEtiqueta(
                        "Emisor electrónico desde:"
                    ),

                comprobantes_electronicos:
                    valorDespuesDeEtiqueta(
                        "Comprobantes Electrónicos:"
                    ),

                afiliado_ple_desde:
                    valorDespuesDeEtiqueta(
                        "Afiliado al PLE desde:"
                    ),

                padrones:
                    listaDespuesDeEtiqueta(
                        "Padrones:"
                    ),

                fecha_consulta:
                    fechaConsulta
            };
        }
        """
    )

    # Si por alguna razón no logró extraer el RUC,
    # conservamos el RUC que intentábamos consultar.
    if not datos.get("ruc"):
        datos["ruc"] = ruc_consultado

    return datos


# ==========================================================
# CONSULTAR UN RUC
# ==========================================================

async def consultar_ruc(page, ruc: str) -> dict:

    for intento in range(
        1,
        MAX_INTENTOS + 1
    ):

        try:

            # ------------------------------------------
            # ABRIR CONSULTA RUC
            # ------------------------------------------

            await page.goto(
                URL_INICIO,
                wait_until="domcontentloaded",
                timeout=30000
            )


            # ------------------------------------------
            # ESPERAR CAMPO RUC
            # ------------------------------------------

            await page.locator(
                "#txtRuc"
            ).wait_for(
                state="visible",
                timeout=15000
            )


            # ------------------------------------------
            # INGRESAR RUC
            # ------------------------------------------

            await page.locator(
                "#txtRuc"
            ).fill(ruc)


            # ------------------------------------------
            # CLICK BUSCAR
            # ------------------------------------------

            async with page.expect_navigation(
                wait_until="domcontentloaded",
                timeout=30000
            ):

                await page.get_by_role(
                    "button",
                    name="Buscar"
                ).click()


            # ------------------------------------------
            # ESPERAR RESPUESTA
            # ------------------------------------------

            await page.wait_for_timeout(
                1000
            )

            contenido = await page.content()


            # ------------------------------------------
            # DETECTAR ERROR SUNAT
            # ------------------------------------------

            if (
                "Surgieron problemas al procesar"
                in contenido
            ):

                raise Exception(
                    "SUNAT devolvió página de error"
                )


            # ------------------------------------------
            # ESPERAR FICHA RESULTADO
            # ------------------------------------------

            await page.get_by_text(
                "Número de RUC:",
                exact=True
            ).wait_for(
                timeout=15000
            )


            # ------------------------------------------
            # EXTRAER INFORMACIÓN
            # ------------------------------------------

            datos = await extraer_datos(page, ruc)

            datos["ok"] = True

            return datos


        except Exception as e:

            print(
                f"      ⚠️ Intento "
                f"{intento}/{MAX_INTENTOS}: "
                f"{e}"
            )

            if intento < MAX_INTENTOS:

                await page.wait_for_timeout(
                    3000
                )


    # Si fallaron todos los intentos

    return {
        "ruc": ruc,
        "ok": False,
        "error":
            "No se pudo consultar después "
            f"de {MAX_INTENTOS} intentos"
    }


# ==========================================================
# MAIN
# ==========================================================

async def main():

    # ------------------------------------------
    # RUC TOTALES
    # ------------------------------------------

    todos_los_rucs = leer_rucs_json(INPUT_JSON)

    print()
    print(
        "RUC únicos en archivo:",
        len(todos_los_rucs)
    )


    # ------------------------------------------
    # CARGAR PROGRESO ANTERIOR
    # ------------------------------------------

    resultados = cargar_resultados_existentes()


    # Consideramos procesados únicamente
    # aquellos que ya están guardados.
    rucs_procesados = {
        str(x.get("ruc"))
        for x in resultados
        if x.get("ruc")
    }


    pendientes = [
        ruc
        for ruc in todos_los_rucs
        if ruc not in rucs_procesados
    ]


    print(
        "Ya procesados:",
        len(rucs_procesados)
    )

    print(
        "Pendientes:",
        len(pendientes)
    )

    print()


    # Si no queda nada por hacer

    if not pendientes:

        print(
            "✅ No quedan RUC pendientes."
        )

        return


    # ------------------------------------------
    # PLAYWRIGHT
    # ------------------------------------------

    async with async_playwright() as p:

        browser = await p.chromium.launch(headless=HEADLESS)

        context = await browser.new_context()

        page = await context.new_page()


        total = len(todos_los_rucs)


        for ruc in pendientes:

            numero_actual = len(resultados) + 1

            print(
                f"[{numero_actual}/{total}] "
                f"Consultando {ruc}..."
            )


            resultado = await consultar_ruc(page, ruc)


            resultados.append(
                resultado
            )


            # --------------------------------------
            # MOSTRAR RESULTADO
            # --------------------------------------

            if resultado.get("ok"):

                print(
                    "   ✅",
                    resultado.get(
                        "razon_social"
                    )
                )

                print(
                    "      Estado:",
                    resultado.get(
                        "estado_contribuyente"
                    )
                )

                print(
                    "      Condición:",
                    resultado.get(
                        "condicion_contribuyente"
                    )
                )

            else:

                print(
                    "   ❌",
                    resultado.get(
                        "error"
                    )
                )


            # --------------------------------------
            # GUARDAR DESPUÉS DE CADA RUC
            # --------------------------------------

            guardar_resultados(
                resultados
            )


            # --------------------------------------
            # PAUSA
            # --------------------------------------

            await asyncio.sleep(
                DELAY_SEGUNDOS
            )


        await browser.close()


    # ==================================================
    # RESUMEN FINAL
    # ==================================================

    exitosos = sum(
        1
        for x in resultados
        if x.get("ok")
    )

    errores = (
        len(resultados)
        - exitosos
    )


    print()
    print("=" * 60)
    print("PROCESO TERMINADO")
    print("=" * 60)

    print(
        "Total:",
        len(resultados)
    )

    print(
        "✅ Exitosos:",
        exitosos
    )

    print(
        "❌ Errores:",
        errores
    )

    print()

    print(
        "Archivo:",
        OUTPUT_JSON
    )


if __name__ == "__main__":
    asyncio.run(main())