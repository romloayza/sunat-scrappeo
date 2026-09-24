# Base consolidada de empresas contratistas de gobiernos regionales

## Base principal

El archivo principal del repositorio es:

`data/data_final_consolidada.csv`

La unidad de observación es:

**empresa (RUC) × gobierno regional (GORE) × año**

La base comprende los años 2021, 2022 y 2024 y combina información de contratación pública, características empresariales, antecedentes de proveedores e información institucional del GORE.

## Diccionario de datos

| Variable | Tipo | Definición / medición |
|---|---|---|
| `ruc` | Texto | Registro Único de Contribuyentes de la empresa. |
| `razon_social` | Texto | Razón social registrada en SUNAT. |
| `nombre_comercial` | Texto | Nombre comercial registrado en SUNAT. |
| `anio` | Entero | Año de la observación contractual: 2021, 2022 o 2024. |
| `gore` | Texto | Gobierno regional con el que la empresa registra contratación durante el año. |
| `fecha_inscripcion` | Fecha | Fecha de inscripción del contribuyente en SUNAT. |
| `fecha_inicio_actividades` | Fecha | Fecha de inicio de actividades registrada en SUNAT. |
| `anio_inicio_actividades` | Entero | Año correspondiente a `fecha_inicio_actividades`. |
| `antiguedad_empresa` | Entero | Años transcurridos entre el inicio de actividades y el año de análisis: `anio - anio_inicio_actividades`. |
| `inicio_posterior_contratacion` | Binaria | Toma valor 1 cuando SUNAT registra una fecha de inicio de actividades posterior al año en que la empresa aparece contratando; 0 en caso contrario. |
| `primer_anio_contratacion` | Entero | Primer año en que el RUC aparece en la base de contrataciones 2004-2024. |
| `experiencia_contratacion` | Entero | Años transcurridos desde la primera contratación observada: `anio - primer_anio_contratacion`. |
| `n_contratos` | Entero | Número de contratos distintos entre la empresa y el GORE durante el año. |
| `n_gores_anio` | Entero | Número de GORE distintos con los que la empresa registra contratación durante ese año. |
| `cmc` | Numérica | Capacidad Máxima de Contratación registrada para el proveedor. |
| `n_contratos_cmc_evaluables` | Entero | Número de contratos empresa-GORE-año para los que existe información suficiente para comparar el monto contractual con el CMC. |
| `n_supera_cmc` | Entero | Número de contratos cuyo monto es superior al CMC de la empresa. |
| `prop_supera_cmc` | Numérica | Proporción de contratos evaluables que superan el CMC: `n_supera_cmc / n_contratos_cmc_evaluables`. |
| `tipo_contribuyente` | Categórica | Tipo de contribuyente registrado en SUNAT. |
| `estado` | Categórica | Estado del contribuyente registrado en SUNAT al momento de la consulta. |
| `condicion` | Categórica | Condición del contribuyente registrada en SUNAT al momento de la consulta. |
| `fecha_baja` | Fecha | Fecha de baja registrada en SUNAT, cuando corresponde. |
| `domicilio` | Texto | Domicilio o ubicación registrada para el proveedor. |
| `actividad_principal` | Texto | Actividad económica principal registrada en SUNAT. |
| `cantidad_rubros` | Entero | Número de actividades económicas principales y secundarias registradas para el RUC. |
| `actividades_economicas` | Texto | Listado completo de actividades económicas registradas para la empresa. |
| `sanciones_tcp_acum` | Entero | Número acumulado de sanciones del Tribunal de Contrataciones Públicas disponible en la fuente de proveedores. |
| `penalidades_acum` | Entero | Número acumulado de penalidades disponible para el proveedor. |
| `inhabilitacion_judicial` | Entero / binaria | Registro de inhabilitación por mandato judicial disponible en la fuente. |
| `inhabilitacion_administrativa` | Entero / binaria | Registro de inhabilitación administrativa disponible en la fuente. |
| `fecha_consulta_sunat` | Fecha/hora | Fecha en que se realizó la consulta del RUC en SUNAT. |
| `sunat_ok` | Binaria | Indicador de procesamiento de la consulta SUNAT. |
| `tiene_info_sunat` | Binaria | Indicador de disponibilidad de información del RUC en la fuente SUNAT utilizada. |
| `tiene_info_proveedores_estado` | Binaria | Indicador de disponibilidad del RUC en la fuente de proveedores del Estado. |
| `puntaje_inco` | Numérica | Puntaje INCO correspondiente al GORE y año de la observación. |
| `rango_inco` | Categórica | Rango asociado al puntaje INCO de la edición correspondiente. |

## Notas de medición

La combinación `ruc + anio + gore` identifica de manera única cada observación.

`n_gores_anio` se calcula a nivel empresa-año. Por ello, si una empresa contrata con tres GORE durante un mismo año, el valor 3 se repite en las tres filas correspondientes.

La superación del CMC se define como:

`monto_contrato > cmc`

Los valores faltantes de CMC se mantienen como faltantes y no se reemplazan por cero.

En contratos asociados a más de una empresa, el monto contractual se conserva para comparar cada RUC con su CMC. No debe interpretarse como el monto individual efectivamente recibido por cada empresa.

`primer_anio_contratacion` y `experiencia_contratacion` se construyen a partir de la base disponible de contrataciones 2004-2024. Por ello, representan experiencia contractual observada en la fuente.

Las variables `estado`, `condicion`, `tipo_contribuyente`, `actividad_principal` y otras características SUNAT corresponden a la información disponible al momento de la consulta y no necesariamente al estado histórico de la empresa en 2021, 2022 o 2024.

Las variables `sanciones_tcp_acum` y `penalidades_acum` son valores acumulados. Al no disponer de la fecha individual de cada sanción o penalidad, no deben interpretarse como antecedentes existentes necesariamente en el año específico de contratación.

El INCO se incorpora a nivel `GORE × año`. Se utilizan únicamente los registros `SEDE CENTRAL`, se excluye Lima Metropolitana y se conserva Lima Provincias como Gobierno Regional de Lima.

## Estructura del repositorio

```text
data/
├── insumos_originales/
├── bases_intermedias/
└── data_final_consolidada.csv

scripts/
├── 01_consolidado_info_empresas.py
├── 02_empresa_gore_anio_base.py
├── 03_consolidar_empresa_gore_anio.py
├── 04_agregar_inco.py
└── 05_validacion_base_maestra.py

scrappeo/
├── scrape_sunat.py
├── scrape_rucs_2021_2022_2024.py
├── limpieza_rucs.py
└── intento1.py
